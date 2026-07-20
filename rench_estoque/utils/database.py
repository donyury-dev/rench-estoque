import sqlite3
import os
from datetime import datetime, timedelta

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'rench_estoque.db')

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()

    # ============================================================
    # 1. TABELA DE CATEGORIAS
    # ============================================================
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS categorias (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL UNIQUE,
            tipo TEXT NOT NULL CHECK(tipo IN ('insumo','equipamento')),
            descricao TEXT,
            data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            data_atualizacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            ativo INTEGER DEFAULT 1
        )
    ''')

    # ============================================================
    # 2. TABELA DE PRODUTOS/INSUMOS
    # ============================================================
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS produtos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            codigo TEXT UNIQUE NOT NULL,
            nome TEXT NOT NULL,
            descricao TEXT,
            categoria_id INTEGER,
            marca TEXT,
            modelo TEXT,
            modelo_compativel TEXT,
            fornecedor TEXT,
            unidade TEXT DEFAULT 'UN',
            estoque_minimo INTEGER DEFAULT 0,
            estoque_maximo INTEGER DEFAULT 0,
            quantidade_atual INTEGER DEFAULT 0,
            localizacao_interna TEXT,
            codigo_barras TEXT,
            caminho_foto TEXT,
            data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            data_atualizacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            ativo INTEGER DEFAULT 1,
            FOREIGN KEY (categoria_id) REFERENCES categorias(id)
        )
    ''')

    # ============================================================
    # 3. TABELA DE EQUIPAMENTOS
    # ============================================================
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS equipamentos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            numero_serie TEXT UNIQUE NOT NULL,
            numero_patrimonio TEXT,
            nome TEXT NOT NULL,
            descricao TEXT,
            categoria_id INTEGER,
            marca TEXT,
            modelo TEXT,
            ano_fabricacao INTEGER,
            status TEXT DEFAULT 'em_estoque' CHECK(status IN ('em_estoque','locado','em_manutencao','descartado')),
            cliente_id INTEGER,
            data_instalacao DATE,
            data_fim_locacao DATE,
            contrato TEXT,
            tecnico_responsavel TEXT,
            caminho_foto TEXT,
            caminho_manual TEXT,
            observacoes TEXT,
            data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            data_atualizacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            ativo INTEGER DEFAULT 1,
            FOREIGN KEY (categoria_id) REFERENCES categorias(id),
            FOREIGN KEY (cliente_id) REFERENCES clientes(id)
        )
    ''')

    # ============================================================
    # 4. TABELA DE CLIENTES
    # ============================================================
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS clientes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cnpj_cpf TEXT,
            razao_social TEXT NOT NULL,
            nome_fantasia TEXT,
            endereco TEXT,
            bairro TEXT,
            cidade TEXT,
            estado TEXT,
            cep TEXT,
            telefone TEXT,
            email TEXT,
            contato_nome TEXT,
            contato_telefone TEXT,
            contrato_ativo TEXT,
            prazo_sla_horas INTEGER DEFAULT 24,
            observacoes TEXT,
            data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            data_atualizacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            ativo INTEGER DEFAULT 1
        )
    ''')

    # ============================================================
    # 5. TABELA DE FORNECEDORES
    # ============================================================
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS fornecedores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cnpj TEXT,
            nome_razao TEXT NOT NULL,
            nome_fantasia TEXT,
            endereco TEXT,
            cidade TEXT,
            estado TEXT,
            telefone TEXT,
            email TEXT,
            representante TEXT,
            prazo_entrega_padrao INTEGER,
            observacoes TEXT,
            data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            ativo INTEGER DEFAULT 1
        )
    ''')

    # ============================================================
    # 6. TABELA DE PRODUTOS FORNECEDORES (preços)
    # ============================================================
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS produto_fornecedor (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            produto_id INTEGER NOT NULL,
            fornecedor_id INTEGER NOT NULL,
            preco REAL,
            prazo_entrega INTEGER,
            data_cotacao DATE,
            FOREIGN KEY (produto_id) REFERENCES produtos(id),
            FOREIGN KEY (fornecedor_id) REFERENCES fornecedores(id),
            UNIQUE(produto_id, fornecedor_id)
        )
    ''')

    # ============================================================
    # 7. TABELA DE MOVIMENTAÇÕES DE ESTOQUE
    # ============================================================
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS movimentacoes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            produto_id INTEGER NOT NULL,
            tipo TEXT NOT NULL CHECK(tipo IN ('entrada','saida','ajuste','transferencia')),
            quantidade INTEGER NOT NULL,
            motivo TEXT NOT NULL,
            referencia TEXT,
            fornecedor_id INTEGER,
            cliente_id INTEGER,
            os_id INTEGER,
            usuario TEXT,
            data_movimentacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (produto_id) REFERENCES produtos(id),
            FOREIGN KEY (fornecedor_id) REFERENCES fornecedores(id),
            FOREIGN KEY (cliente_id) REFERENCES clientes(id)
        )
    ''')

    # ============================================================
    # 8. TABELA DE ORDENS DE SERVIÇO
    # ============================================================
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS ordens_servico (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            numero_os TEXT UNIQUE NOT NULL,
            cliente_id INTEGER NOT NULL,
            equipamento_id INTEGER,
            descricao_problema TEXT NOT NULL,
            solucao_aplicada TEXT,
            pecas_trocadas TEXT,
            tecnico_id TEXT,
            tecnico_nome TEXT,
            prioridade TEXT DEFAULT 'media' CHECK(prioridade IN ('baixa','media','alta','urgente')),
            status TEXT DEFAULT 'aberta' CHECK(status IN ('aberta','em_andamento','aguardando_peca','concluida','cancelada')),
            data_abertura TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            data_previsao DATE,
            data_conclusao TIMESTAMP,
            tempo_gasto_minutos INTEGER,
            assinatura_cliente TEXT,
            observacoes TEXT,
            FOREIGN KEY (cliente_id) REFERENCES clientes(id),
            FOREIGN KEY (equipamento_id) REFERENCES equipamentos(id)
        )
    ''')

    # ============================================================
    # 9. TABELA DE MANUTENÇÕES PREVENTIVAS
    # ============================================================
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS manutencoes_preventivas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            equipamento_id INTEGER NOT NULL,
            periodicidade_dias INTEGER,
            periodicidade_paginas INTEGER,
            proxima_data DATE,
            proximo_contador INTEGER,
            observacoes TEXT,
            ativo INTEGER DEFAULT 1,
            FOREIGN KEY (equipamento_id) REFERENCES equipamentos(id)
        )
    ''')

    # ============================================================
    # 10. TABELA DE USUÁRIOS
    # ============================================================
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            usuario TEXT UNIQUE NOT NULL,
            senha_hash TEXT NOT NULL,
            email TEXT,
            nivel_acesso TEXT DEFAULT 'tecnico' CHECK(nivel_acesso IN ('administrador','gerente','tecnico','leitura')),
            data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            ativo INTEGER DEFAULT 1
        )
    ''')

    # ============================================================
    # 11. TABELA DE LOG DE AUDITORIA
    # ============================================================
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS auditoria (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario TEXT,
            acao TEXT NOT NULL,
            tabela TEXT,
            registro_id INTEGER,
            dados_anteriores TEXT,
            dados_novos TEXT,
            data_hora TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # ============================================================
    # 12. TABELA DE VINCULO EQUIPAMENTO-PRODUTO (compatibilidade)
    # ============================================================
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS equipamento_produto_compativel (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            equipamento_id INTEGER NOT NULL,
            produto_id INTEGER NOT NULL,
            FOREIGN KEY (equipamento_id) REFERENCES equipamentos(id),
            FOREIGN KEY (produto_id) REFERENCES produtos(id),
            UNIQUE(equipamento_id, produto_id)
        )
    ''')

    # ============================================================
    # CETEGORIAS PADRAO
    # ============================================================
    categorias_padrao = [
        ('Toner', 'insumo', 'Cartuchos de toner para impressoras'),
        ('Drum / Fotocondutor', 'insumo', 'Cilindros fotocondutores'),
        ('Esteira', 'insumo', 'Esteiras de transferência'),
        ('Fusor', 'insumo', 'Unidades de fusão'),
        ('Coletor', 'insumo', 'Coletores de resíduos'),
        ('Tinta', 'insumo', 'Tintas para impressoras jato de tinta'),
        ('Papel Fotográfico', 'insumo', 'Papel fotográfico especial'),
        ('Impressora', 'equipamento', 'Equipamentos de impressão'),
        ('Computador', 'equipamento', 'Desktops e notebooks'),
        ('Servidor', 'equipamento', 'Servidores e storage'),
        ('Etiquetadora', 'equipamento', 'Impressoras de etiquetas'),
        ('Monitor', 'equipamento', 'Monitores e displays'),
        ('CPU', 'equipamento', 'Processadores e unidades centrais'),
    ]

    cursor.executemany('''
        INSERT OR IGNORE INTO categorias (nome, tipo, descricao)
        VALUES (?, ?, ?)
    ''', categorias_padrao)

    # ============================================================
    # USUARIO ADMIN PADRAO (senha: admin123)
    # ============================================================
    import hashlib
    senha_hash = hashlib.sha256('admin123'.encode()).hexdigest()
    cursor.execute('''
        INSERT OR IGNORE INTO usuarios (nome, usuario, senha_hash, email, nivel_acesso)
        VALUES (?, ?, ?, ?, ?)
    ''', ('Administrador', 'admin', senha_hash, 'admin@rench.com.br', 'administrador'))

    conn.commit()
    conn.close()
    print("Banco de dados inicializado com sucesso!")

if __name__ == '__main__':
    init_db()
