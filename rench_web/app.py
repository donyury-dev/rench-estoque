import os
import sqlite3
import hashlib
import difflib
import unicodedata
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, g, session
from functools import wraps

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'rench_estoque_2026_segredo')

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE = os.path.join(BASE_DIR, 'rench_web.db')
PLANILHA_PADRAO = os.path.join(os.path.dirname(BASE_DIR), 'data_atual.xlsx')

PREFIXOS_RASTREIO = {
    "impressora": "IMP",
    "desktop": "CPU",
    "notebook": "NOT",
    "servidor": "SRV",
    "monitor": "MON",
    "periferico": "PER",
}

def normalizar_busca(texto):
    texto = str(texto or "").lower().strip()
    texto = unicodedata.normalize("NFKD", texto)
    texto = "".join(ch for ch in texto if not unicodedata.combining(ch))
    return "".join(ch if ch.isalnum() else " " for ch in texto)

def preparar_termos_busca(texto):
    normalizado = normalizar_busca(texto)
    return [termo for termo in normalizado.split() if termo]

def texto_combinado(*valores):
    return normalizar_busca(" ".join(str(valor or "") for valor in valores))

def calcular_pontuacao_busca(termos, *valores):
    alvo = texto_combinado(*valores)
    if not termos or not alvo:
        return 0

    pontuacao = 0
    palavras = alvo.split()
    for termo in termos:
        if termo in alvo:
            pontuacao += 100
            continue

        melhor = 0
        for palavra in palavras:
            similaridade = difflib.SequenceMatcher(None, termo, palavra).ratio()
            if similaridade > melhor:
                melhor = similaridade

        if melhor >= 0.78:
            pontuacao += int(melhor * 80)
        elif melhor >= 0.68:
            pontuacao += int(melhor * 55)

    return pontuacao

def buscar_sugestoes_locais(cur, busca, limite=6):
    termos = preparar_termos_busca(busca)
    if not termos:
        return []

    cur.execute("""
        SELECT e.nome as empresa_nome, e.tipo as empresa_tipo, u.nome as unidade_nome, u.setor
        FROM empresas e
        LEFT JOIN unidades u ON u.empresa_id = e.id AND u.ativo=1
        WHERE e.ativo=1
    """)

    sugestoes = []
    for local in cur.fetchall():
        pontuacao = calcular_pontuacao_busca(
            termos,
            local["empresa_nome"],
            local["empresa_tipo"],
            local["unidade_nome"],
            local["setor"],
        )
        if pontuacao:
            sugestoes.append({
                "empresa": local["empresa_nome"],
                "tipo": local["empresa_tipo"],
                "unidade": local["unidade_nome"],
                "setor": local["setor"],
                "pontuacao": pontuacao,
            })

    sugestoes.sort(key=lambda item: item["pontuacao"], reverse=True)
    return sugestoes[:limite]

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row
    return db

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

def init_db():
    db = sqlite3.connect(DATABASE)
    cur = db.cursor()

    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='equipamentos'")
    tabela_equipamentos = cur.fetchone()
    if tabela_equipamentos:
        cur.execute("PRAGMA table_info(equipamentos)")
        colunas_existentes = {row[1] for row in cur.fetchall()}
        if 'tipo_equipamento' not in colunas_existentes:
            cur.execute("DROP TABLE IF EXISTS movimentacoes")
            cur.execute("DROP TABLE IF EXISTS historico_defeitos")
            cur.execute("DROP TABLE IF EXISTS defeitos")
            cur.execute("DROP TABLE IF EXISTS equipamentos")
            cur.execute("DROP TABLE IF EXISTS locais")

    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='empresas'")
    if not cur.fetchone():
        # Migracao de locais -> empresas+unidades
        cur.execute("CREATE TABLE IF NOT EXISTS locais_backup AS SELECT * FROM locais" if cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='locais'").fetchone() else "SELECT 1")

    # TABELA: empresas/fornecedores (matriz)
    cur.execute('''
        CREATE TABLE IF NOT EXISTS empresas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            tipo TEXT DEFAULT 'cliente',
            ativo INTEGER DEFAULT 1
        )
    ''')

    # TABELA: unidades (filial)
    cur.execute('''
        CREATE TABLE IF NOT EXISTS unidades (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            empresa_id INTEGER NOT NULL,
            nome TEXT NOT NULL,
            setor TEXT,
            ativo INTEGER DEFAULT 1,
            FOREIGN KEY (empresa_id) REFERENCES empresas(id)
        )
    ''')

    # TABELA: equipamentos (atualizada com todos os campos dos desenhos)
    cur.execute('''
        CREATE TABLE IF NOT EXISTS equipamentos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            codigo TEXT,
            tipo_equipamento TEXT NOT NULL CHECK(tipo_equipamento IN ('impressora','desktop','notebook','servidor','monitor','periferico')),
            fabricante TEXT,
            modelo TEXT NOT NULL,
            numero_serie TEXT,
            patrimonio TEXT,
            
            -- Campos especificos IMPRESSORA
            funcao TEXT CHECK(funcao IN ('impressora','multifuncional')),
            tipo_impressao TEXT CHECK(tipo_impressao IN ('laser','jato_de_tinta','etiqueta','termica')),
            tamanho_papel TEXT CHECK(tamanho_papel IN ('A3','A4','etiqueta','cupom')),
            funcionalidades TEXT,
            contador_mono INTEGER DEFAULT 0,
            contador_color INTEGER DEFAULT 0,
            
            -- Campos especificos COMPUTADOR/SERVIDOR
            processador_modelo TEXT,
            processador_geracao TEXT,
            processador_velocidade TEXT,
            memoria_capacidade TEXT,
            memoria_tipo TEXT,
            memoria_barramento TEXT,
            memoria_velocidade TEXT,
            armazenamento_1_capacidade TEXT,
            armazenamento_1_tipo TEXT,
            armazenamento_2_capacidade TEXT,
            armazenamento_2_tipo TEXT,
            armazenamento_3_capacidade TEXT,
            armazenamento_3_tipo TEXT,
            
            -- Campos comuns
            status TEXT DEFAULT 'ativo' CHECK(status IN ('ativo','inativo')),
            local_atual_id INTEGER,
            unidade_id INTEGER,
            local_atual_nome TEXT,
            cliente_atual TEXT,
            observacoes TEXT,
            data_cadastro TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            ativo INTEGER DEFAULT 1,
            FOREIGN KEY (unidade_id) REFERENCES unidades(id)
        )
    ''')

    # TABELA: movimentacoes
    cur.execute('''
        CREATE TABLE IF NOT EXISTS movimentacoes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            equipamento_id INTEGER NOT NULL,
            data_movimentacao DATE NOT NULL,
            origem_local TEXT,
            origem_unidade TEXT,
            destino_local TEXT NOT NULL,
            destino_unidade TEXT,
            tipo_movimento TEXT NOT NULL CHECK(tipo_movimento IN (
                'entrada_estoque','saida_cliente','retorno_cliente',
                'envio_manutencao','retorno_manutencao','transferencia'
            )),
            responsavel TEXT,
            observacoes TEXT,
            FOREIGN KEY (equipamento_id) REFERENCES equipamentos(id)
        )
    ''')

    # TABELA: historico_defeitos
    cur.execute('''
        CREATE TABLE IF NOT EXISTS historico_defeitos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            equipamento_id INTEGER NOT NULL,
            data_ocorrencia DATE DEFAULT CURRENT_DATE,
            descricao TEXT NOT NULL,
            status TEXT DEFAULT 'pendente' CHECK(status IN ('pendente','resolvido')),
            FOREIGN KEY (equipamento_id) REFERENCES equipamentos(id)
        )
    ''')

    # TABELA: usuarios
    cur.execute('''
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            usuario TEXT UNIQUE NOT NULL,
            senha_hash TEXT NOT NULL,
            nivel TEXT DEFAULT 'tecnico' CHECK(nivel IN ('admin','gerente','tecnico')),
            ativo INTEGER DEFAULT 1
        )
    ''')

    # Usuario admin padrao
    senha_hash = hashlib.sha256('admin123'.encode()).hexdigest()
    cur.execute('''
        INSERT OR IGNORE INTO usuarios (nome, usuario, senha_hash, nivel)
        VALUES ('Administrador', 'admin', ?, 'admin')
    ''', (senha_hash,))

    # EMPRESAS / UNIDADES PADRAO
    # Proteger nova tabela locais caso já tenha dados
    cur.execute("SELECT COUNT(*) FROM empresas")
    if cur.fetchone()[0] == 0:
        padrao_empresas = [
            ('RENCH', 'rench'),
            ('SAMIR', 'cliente'),
            ('AES', 'cliente'),
            ('Mercadão', 'cliente'),
            ('Stuttgart Porsche', 'cliente'),
            ('R10', 'assistencia'),
        ]
        for nome, tipo in padrao_empresas:
            cur.execute("INSERT INTO empresas (nome, tipo) VALUES (?, ?)", (nome, tipo))
        # Associar unidades padrão de RENCH
        cur.execute("SELECT id FROM empresas WHERE nome='RENCH'")
        rench_id = cur.fetchone()[0]
        cur.execute("INSERT INTO unidades (empresa_id, nome, setor) VALUES (?, ?, ?)", (rench_id, 'RENCH - Estoque', 'Estoque principal'))
        cur.execute("INSERT INTO unidades (empresa_id, nome, setor) VALUES (?, ?, ?)", (rench_id, 'RENCH - Depósito', 'Depósito secundário'))
        # R10 unidade padrão
        cur.execute("SELECT id FROM empresas WHERE nome='R10'")
        r10_id = cur.fetchone()[0]
        cur.execute("INSERT INTO unidades (empresa_id, nome, setor) VALUES (?, ?, ?)", (r10_id, 'R10 - Matriz SP', 'Assistência técnica'))

    db.commit()
    db.close()
    print("Banco de dados inicializado!")

def _normalizar_texto(valor):
    if valor is None:
        return None
    texto = str(valor).strip()
    return texto if texto else None

def _normalizar_data(valor):
    if valor is None:
        return None
    if hasattr(valor, "strftime"):
        return valor.strftime("%Y-%m-%d")
    return str(valor)[:10]

def _mapear_tipo_movimento(valor):
    texto = (_normalizar_texto(valor) or "").lower()
    if "envio" in texto and "cliente" in texto:
        return "saida_cliente"
    if "retorno" in texto and "cliente" in texto:
        return "retorno_cliente"
    if "envio" in texto and ("manuten" in texto or "manutenc" in texto):
        return "envio_manutencao"
    if "retorno" in texto and ("manuten" in texto or "manutenc" in texto):
        return "retorno_manutencao"
    if "entrada" in texto:
        return "entrada_estoque"
    return "transferencia"

def _mapear_tipo_computador(valor):
    texto = (_normalizar_texto(valor) or "").lower()
    if "server" in texto or "servidor" in texto:
        return "servidor"
    if "note" in texto:
        return "notebook"
    if "monitor" in texto:
        return "monitor"
    if "desktop" in texto or "comput" in texto:
        return "desktop"
    return "periferico"

def _descobrir_fabricante(modelo):
    texto = (_normalizar_texto(modelo) or "").upper()
    marcas = ["OKI", "EPSON", "HP", "DELL", "ZEBRA", "RICOH", "LENOVO", "SUPER MICRO", "SUPERMICRO"]
    for marca in marcas:
        if marca in texto:
            return "Supermicro" if marca in ("SUPER MICRO", "SUPERMICRO") else marca.title()
    return None

def gerar_codigo_rastreio(cur, tipo_equipamento):
    prefixo = PREFIXOS_RASTREIO.get(tipo_equipamento, "EQP")
    cur.execute(
        "SELECT codigo FROM equipamentos WHERE tipo_equipamento=? AND codigo LIKE ?",
        (tipo_equipamento, f"RCH-{prefixo}-%")
    )
    numeros = []
    for row in cur.fetchall():
        try:
            numeros.append(int(row[0].split("-")[-1]))
        except (TypeError, ValueError, IndexError):
            pass
    proximo_numero = (max(numeros) if numeros else 0) + 1
    codigo = f"RCH-{prefixo}-{proximo_numero:06d}"

    while True:
        cur.execute("SELECT id FROM equipamentos WHERE codigo=?", (codigo,))
        if not cur.fetchone():
            return codigo
        proximo_numero += 1
        codigo = f"RCH-{prefixo}-{proximo_numero:06d}"

def importar_planilha_para_banco(caminho=PLANILHA_PADRAO, limpar=True):
    import openpyxl

    if not os.path.exists(caminho):
        raise FileNotFoundError(f"Planilha não encontrada: {caminho}")

    db = sqlite3.connect(DATABASE)
    db.row_factory = sqlite3.Row
    cur = db.cursor()

    if limpar:
        cur.execute("DELETE FROM movimentacoes")
        cur.execute("DELETE FROM historico_defeitos")
        cur.execute("DELETE FROM equipamentos")

    wb = openpyxl.load_workbook(caminho, data_only=True)
    importados = {"impressoras": 0, "computadores": 0, "movimentacoes": 0, "defeitos": 0}

    if "IMPRESSORA" in wb.sheetnames:
        ws = wb["IMPRESSORA"]
        for row in ws.iter_rows(min_row=3, values_only=True):
            data, modelo, serie, contador, movimento, local_coleta, local_atual, motivo, item_id = row[:9]
            modelo = _normalizar_texto(modelo)
            serie = _normalizar_texto(serie)
            if not modelo and not serie:
                continue
            if not modelo:
                modelo = "Modelo não informado"
            local_atual = _normalizar_texto(local_atual) or "RENCH - Estoque"
            local_coleta = _normalizar_texto(local_coleta)
            contador = int(contador) if isinstance(contador, (int, float)) else 0

            cur.execute("SELECT id FROM equipamentos WHERE numero_serie=?", (serie,))
            existente = cur.fetchone() if serie else None
            if existente:
                equipamento_id = existente["id"]
                cur.execute("""
                    UPDATE equipamentos
                    SET modelo=?, fabricante=COALESCE(fabricante, ?), local_atual_nome=?,
                        contador_mono=?, tipo_equipamento='impressora'
                    WHERE id=?
                """, (modelo, _descobrir_fabricante(modelo), local_atual, contador, equipamento_id))
            else:
                cur.execute("""
                    INSERT INTO equipamentos (
                        codigo, tipo_equipamento, fabricante, modelo, numero_serie,
                        funcao, tipo_impressao, contador_mono, local_atual_nome,
                        status, observacoes
                    ) VALUES (?, 'impressora', ?, ?, ?, 'impressora', 'laser', ?, ?, 'ativo', ?)
                """, (gerar_codigo_rastreio(cur, "impressora"), _descobrir_fabricante(modelo), modelo, serie, contador, local_atual, _normalizar_texto(motivo)))
                equipamento_id = cur.lastrowid
                importados["impressoras"] += 1

            if data or movimento or local_coleta or local_atual:
                cur.execute("""
                    INSERT INTO movimentacoes (
                        equipamento_id, data_movimentacao, origem_local, destino_local,
                        tipo_movimento, observacoes
                    ) VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    equipamento_id,
                    _normalizar_data(data) or datetime.now().strftime("%Y-%m-%d"),
                    local_coleta,
                    local_atual,
                    _mapear_tipo_movimento(movimento),
                    _normalizar_texto(movimento) or _normalizar_texto(motivo)
                ))
                importados["movimentacoes"] += 1

    if "COMP-NOTE" in wb.sheetnames:
        ws = wb["COMP-NOTE"]
        for row in ws.iter_rows(min_row=3, values_only=True):
            data, tipo, modelo, serie, movimento, local_coleta, local_atual, motivo, item_id, config = row[:10]
            modelo = _normalizar_texto(modelo)
            serie = _normalizar_texto(serie)
            if not modelo and not serie:
                continue
            if not modelo:
                modelo = "Modelo não informado"
            tipo_equipamento = _mapear_tipo_computador(tipo)
            local_atual = _normalizar_texto(local_atual) or "RENCH - Estoque"
            local_coleta = _normalizar_texto(local_coleta)

            cur.execute("SELECT id FROM equipamentos WHERE numero_serie=?", (serie,))
            existente = cur.fetchone() if serie else None
            if existente:
                equipamento_id = existente["id"]
                cur.execute("""
                    UPDATE equipamentos
                    SET modelo=?, fabricante=COALESCE(fabricante, ?), local_atual_nome=?,
                        tipo_equipamento=?
                    WHERE id=?
                """, (modelo, _descobrir_fabricante(modelo), local_atual, tipo_equipamento, equipamento_id))
            else:
                cur.execute("""
                    INSERT INTO equipamentos (
                        codigo, tipo_equipamento, fabricante, modelo, numero_serie,
                        local_atual_nome, status, observacoes
                    ) VALUES (?, ?, ?, ?, ?, ?, 'ativo', ?)
                """, (gerar_codigo_rastreio(cur, tipo_equipamento), tipo_equipamento, _descobrir_fabricante(modelo), modelo, serie, local_atual, _normalizar_texto(config) or _normalizar_texto(motivo)))
                equipamento_id = cur.lastrowid
                importados["computadores"] += 1

            if data or movimento or local_coleta or local_atual:
                cur.execute("""
                    INSERT INTO movimentacoes (
                        equipamento_id, data_movimentacao, origem_local, destino_local,
                        tipo_movimento, observacoes
                    ) VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    equipamento_id,
                    _normalizar_data(data) or datetime.now().strftime("%Y-%m-%d"),
                    local_coleta,
                    local_atual,
                    _mapear_tipo_movimento(movimento),
                    _normalizar_texto(movimento) or _normalizar_texto(motivo)
                ))
                importados["movimentacoes"] += 1

    if "Planilha1" in wb.sheetnames:
        ws = wb["Planilha1"]
        for row in ws.iter_rows(values_only=True):
            serie = _normalizar_texto(row[0] if len(row) > 0 else None)
            defeito = _normalizar_texto(row[1] if len(row) > 1 else None)
            if not serie or not defeito:
                continue
            cur.execute("SELECT id FROM equipamentos WHERE numero_serie=?", (serie,))
            equip = cur.fetchone()
            if equip:
                cur.execute("""
                    INSERT INTO historico_defeitos (equipamento_id, descricao)
                    VALUES (?, ?)
                """, (equip["id"], defeito))
                importados["defeitos"] += 1

    db.commit()
    db.close()
    return importados

# ============================================================
# ROTAS
# ============================================================

USUARIO_PADRAO = 'admin'
SENHA_PADRAO_HASH = hashlib.sha256('ipascnma'.encode()).hexdigest()

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logado'):
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        usuario = request.form.get('usuario', '').strip()
        senha = request.form.get('senha', '')
        senha_hash = hashlib.sha256(senha.encode()).hexdigest()
        if usuario == USUARIO_PADRAO and senha_hash == SENHA_PADRAO_HASH:
            session['logado'] = True
            session['usuario'] = usuario
            return redirect(url_for('index'))
        flash('Usuário ou senha incorretos.', 'danger')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/')
@login_required
def index():
    db = get_db()
    cur = db.cursor()

    # Contagens por tipo
    cur.execute("SELECT tipo_equipamento, COUNT(*) as qtd FROM equipamentos WHERE ativo=1 GROUP BY tipo_equipamento")
    por_tipo = {r['tipo_equipamento']: r['qtd'] for r in cur.fetchall()}

    # Contagens por local
    cur.execute("SELECT local_atual_nome, COUNT(*) as qtd FROM equipamentos WHERE ativo=1 AND local_atual_nome IS NOT NULL GROUP BY local_atual_nome")
    por_local = cur.fetchall()

    # Ultimas movimentacoes (somente datas validas)
    cur.execute("""
        SELECT m.data_movimentacao, e.tipo_equipamento, e.modelo, e.numero_serie, m.tipo_movimento, m.destino_local, m.responsavel
        FROM movimentacoes m
        JOIN equipamentos e ON m.equipamento_id = e.id
        WHERE m.data_movimentacao LIKE '____-__-__'
        ORDER BY m.data_movimentacao DESC, m.id DESC
        LIMIT 8
    """)
    ultimas_mov = cur.fetchall()

    return render_template('dashboard.html',
        por_tipo=por_tipo, por_local=por_local, ultimas_mov=ultimas_mov
    )

@app.route('/importar-planilha', methods=['POST'])
@login_required
def importar_planilha():
    try:
        resultado = importar_planilha_para_banco()
        flash(
            f"Planilha importada: {resultado['impressoras']} impressoras, "
            f"{resultado['computadores']} computadores/notebooks/servidores, "
            f"{resultado['movimentacoes']} movimentações e {resultado['defeitos']} defeitos.",
            "success"
        )
    except Exception as erro:
        flash(f"Erro ao importar planilha: {erro}", "danger")
    return redirect(url_for('lista_equipamentos'))

@app.route('/equipamentos')
@login_required
def lista_equipamentos():
    db = get_db()
    cur = db.cursor()
    tipo = request.args.get('tipo', '')
    busca = request.args.get('q', '')
    mov_recente = request.args.get('mov_recente', '')
    sugestoes = []

    sql = """
        SELECT e.*, COALESCE(u.nome, e.local_atual_nome) as local_nome,
               emp.nome as empresa_nome, u.setor as unidade_setor,
               m.ultima_movimentacao
        FROM equipamentos e
        LEFT JOIN unidades u ON e.unidade_id = u.id
        LEFT JOIN empresas emp ON emp.id = u.empresa_id
        LEFT JOIN (
            SELECT equipamento_id, MAX(data_movimentacao) as ultima_movimentacao
            FROM movimentacoes
            WHERE data_movimentacao LIKE '____-__-__'
            GROUP BY equipamento_id
        ) m ON m.equipamento_id = e.id
        WHERE e.ativo=1
    """
    params = []

    if tipo:
        sql += " AND e.tipo_equipamento = ?"
        params.append(tipo)
    sql += " ORDER BY e.tipo_equipamento, e.modelo"

    cur.execute(sql, params)
    equipamentos = cur.fetchall()

    if busca:
        termos = preparar_termos_busca(busca)
        filtrados = []
        for equipamento in equipamentos:
            pontuacao = calcular_pontuacao_busca(
                termos,
                equipamento["codigo"],
                equipamento["fabricante"],
                equipamento["modelo"],
                equipamento["numero_serie"],
                equipamento["patrimonio"],
                equipamento["cliente_atual"],
                equipamento["local_nome"],
                equipamento["empresa_nome"],
                equipamento["unidade_setor"],
            )
            if pontuacao >= 180:
                filtrados.append((pontuacao, equipamento))

        filtrados.sort(key=lambda item: item[0], reverse=True)
        equipamentos = [item[1] for item in filtrados]
        sugestoes = buscar_sugestoes_locais(cur, busca)

    return render_template('equipamentos.html',
        equipamentos=equipamentos, filtro_tipo=tipo, filtro_mov=mov_recente, busca=busca, sugestoes=sugestoes
    )

@app.route('/equipamento/<int:equip_id>')
@login_required
def detalhe_equipamento(equip_id):
    db = get_db()
    cur = db.cursor()

    cur.execute("SELECT * FROM equipamentos WHERE id=? AND ativo=1", (equip_id,))
    equip = cur.fetchone()
    if not equip:
        flash("Equipamento nao encontrado!", "danger")
        return redirect(url_for('lista_equipamentos'))

    cur.execute("SELECT * FROM movimentacoes WHERE equipamento_id=? ORDER BY data_movimentacao DESC, id DESC", (equip_id,))
    movimentacoes = cur.fetchall()

    cur.execute("SELECT * FROM historico_defeitos WHERE equipamento_id=? ORDER BY data_ocorrencia DESC", (equip_id,))
    defeitos = cur.fetchall()

    return render_template('equipamento_detalhe.html',
        equip=equip, movimentacoes=movimentacoes, defeitos=defeitos
    )

@app.route('/equipamento/novo', methods=['GET', 'POST'])
@login_required
def novo_equipamento():
    db = get_db()
    cur = db.cursor()

    if request.method == 'POST':
        tipo = request.form['tipo_equipamento']
        # Resolve empresa -> unidade
        unidade_id = request.form.get('unidade_id') or None
        local_atual_nome = request.form.get('local_atual_nome')
        if unidade_id:
            cur.execute("SELECT u.nome, e.nome FROM unidades u JOIN empresas e ON e.id=u.empresa_id WHERE u.id=?", (unidade_id,))
            unidade = cur.fetchone()
            if unidade:
                local_atual_nome = unidade[0]
                cliente_atual = unidade[1]
            else:
                cliente_atual = None
        else:
            cliente_atual = None
        # Campos comuns
        campos = {
            'codigo': gerar_codigo_rastreio(cur, tipo),
            'tipo_equipamento': tipo,
            'fabricante': request.form.get('fabricante'),
            'modelo': request.form.get('modelo'),
            'numero_serie': request.form.get('numero_serie'),
            'patrimonio': request.form.get('patrimonio'),
            'status': request.form.get('status', 'ativo'),
            'unidade_id': unidade_id,
            'local_atual_nome': local_atual_nome,
            'cliente_atual': cliente_atual,
            'observacoes': request.form.get('observacoes'),
        }

        # Campos especificos por tipo
        if tipo == 'impressora':
            campos.update({
                'funcao': request.form.get('funcao'),
                'tipo_impressao': request.form.get('tipo_impressao'),
                'tamanho_papel': request.form.get('tamanho_papel'),
                'funcionalidades': request.form.get('funcionalidades'),
                'contador_mono': request.form.get('contador_mono', 0),
                'contador_color': request.form.get('contador_color', 0),
            })
        else:
            campos.update({
                'processador_modelo': request.form.get('processador_modelo'),
                'processador_geracao': request.form.get('processador_geracao'),
                'processador_velocidade': request.form.get('processador_velocidade'),
                'memoria_capacidade': request.form.get('memoria_capacidade'),
                'memoria_tipo': request.form.get('memoria_tipo'),
                'memoria_velocidade': request.form.get('memoria_velocidade'),
                'armazenamento_1_capacidade': request.form.get('armazenamento_1_capacidade'),
                'armazenamento_1_tipo': request.form.get('armazenamento_1_tipo'),
                'armazenamento_2_capacidade': request.form.get('armazenamento_2_capacidade'),
                'armazenamento_2_tipo': request.form.get('armazenamento_2_tipo'),
                'armazenamento_3_capacidade': request.form.get('armazenamento_3_capacidade'),
                'armazenamento_3_tipo': request.form.get('armazenamento_3_tipo'),
            })

        # Montar SQL dinamico
        colunas = [k for k, v in campos.items() if v is not None]
        valores = [campos[k] for k in colunas]
        placeholders = ','.join(['?' for _ in colunas])

        sql = f"INSERT INTO equipamentos ({','.join(colunas)}) VALUES ({placeholders})"
        cur.execute(sql, valores)
        db.commit()

        flash("Equipamento cadastrado com sucesso!", "success")
        return redirect(url_for('lista_equipamentos'))

    # GET - carregar empresas e unidades para o formulario
    cur.execute("""
        SELECT e.id as empresa_id, e.nome as empresa_nome, e.tipo as empresa_tipo,
               u.id as unidade_id, u.nome as unidade_nome, u.setor
        FROM empresas e
        LEFT JOIN unidades u ON u.empresa_id = e.id AND u.ativo=1
        WHERE e.ativo=1
        ORDER BY e.tipo DESC, e.nome, u.nome
    """)
    locais = cur.fetchall()

    return render_template('equipamento_form.html', equip=None, locais=locais)

@app.route('/equipamento/<int:equip_id>/editar', methods=['GET', 'POST'])
@login_required
def editar_equipamento(equip_id):
    db = get_db()
    cur = db.cursor()

    cur.execute("SELECT * FROM equipamentos WHERE id=? AND ativo=1", (equip_id,))
    equip = cur.fetchone()
    if not equip:
        flash("Equipamento nao encontrado!", "danger")
        return redirect(url_for('lista_equipamentos'))

    if request.method == 'POST':
        unidade_id = request.form.get('unidade_id') or None
        local_atual_nome = request.form.get('local_atual_nome')
        cliente_atual = None

        if unidade_id:
            cur.execute("""
                SELECT u.nome as unidade_nome, e.nome as empresa_nome
                FROM unidades u
                JOIN empresas e ON e.id = u.empresa_id
                WHERE u.id=?
            """, (unidade_id,))
            unidade = cur.fetchone()
            if unidade:
                local_atual_nome = unidade['unidade_nome']
                cliente_atual = unidade['empresa_nome']

        campos = {
            'fabricante': request.form.get('fabricante'),
            'modelo': request.form.get('modelo'),
            'numero_serie': request.form.get('numero_serie'),
            'patrimonio': request.form.get('patrimonio'),
            'status': request.form.get('status', 'ativo'),
            'unidade_id': unidade_id,
            'local_atual_nome': local_atual_nome,
            'cliente_atual': cliente_atual,
            'observacoes': request.form.get('observacoes'),
            'funcao': request.form.get('funcao') or None,
            'tipo_impressao': request.form.get('tipo_impressao') or None,
            'tamanho_papel': request.form.get('tamanho_papel') or None,
            'funcionalidades': request.form.get('funcionalidades'),
            'contador_mono': request.form.get('contador_mono') or 0,
            'contador_color': request.form.get('contador_color') or 0,
            'processador_modelo': request.form.get('processador_modelo'),
            'processador_geracao': request.form.get('processador_geracao'),
            'processador_velocidade': request.form.get('processador_velocidade'),
            'memoria_capacidade': request.form.get('memoria_capacidade'),
            'memoria_tipo': request.form.get('memoria_tipo'),
            'memoria_velocidade': request.form.get('memoria_velocidade'),
            'armazenamento_1_capacidade': request.form.get('armazenamento_1_capacidade'),
            'armazenamento_1_tipo': request.form.get('armazenamento_1_tipo'),
            'armazenamento_2_capacidade': request.form.get('armazenamento_2_capacidade'),
            'armazenamento_2_tipo': request.form.get('armazenamento_2_tipo'),
            'armazenamento_3_capacidade': request.form.get('armazenamento_3_capacidade'),
            'armazenamento_3_tipo': request.form.get('armazenamento_3_tipo'),
        }

        set_sql = ', '.join([f"{campo}=?" for campo in campos])
        valores = list(campos.values()) + [equip_id]
        cur.execute(f"UPDATE equipamentos SET {set_sql} WHERE id=?", valores)
        db.commit()

        flash("Equipamento atualizado com sucesso!", "success")
        return redirect(url_for('detalhe_equipamento', equip_id=equip_id))

    cur.execute("""
        SELECT e.id as empresa_id, e.nome as empresa_nome, e.tipo as empresa_tipo,
               u.id as unidade_id, u.nome as unidade_nome, u.setor
        FROM empresas e
        LEFT JOIN unidades u ON u.empresa_id = e.id AND u.ativo=1
        WHERE e.ativo=1
        ORDER BY e.tipo DESC, e.nome, u.nome
    """)
    locais = cur.fetchall()

    return render_template('equipamento_editar.html', equip=equip, locais=locais)

@app.route('/equipamento/<int:equip_id>/excluir', methods=['POST'])
@login_required
def excluir_equipamento(equip_id):
    db = get_db()
    cur = db.cursor()
    cur.execute("UPDATE equipamentos SET ativo=0 WHERE id=?", (equip_id,))
    db.commit()
    flash('Equipamento exclu?do com sucesso.', 'success')
    return redirect(url_for('lista_equipamentos'))

@app.route('/movimentar/<int:equip_id>', methods=['GET', 'POST'])
@login_required
def movimentar(equip_id):
    db = get_db()
    cur = db.cursor()

    cur.execute("SELECT e.*, u.nome as unidade_nome, emp.nome as empresa_nome FROM equipamentos e LEFT JOIN unidades u ON u.id=e.unidade_id LEFT JOIN empresas emp ON emp.id=u.empresa_id WHERE e.id=?", (equip_id,))
    equip = cur.fetchone()
    if not equip:
        flash("Equipamento nao encontrado!", "danger")
        return redirect(url_for('lista_equipamentos'))

    if request.method == 'POST':
        tipo_mov = request.form['tipo_movimento']
        data_mov = request.form['data_movimentacao']
        destino_unidade_id = request.form.get('destino_unidade_id')
        responsavel = request.form.get('responsavel')
        obs = request.form.get('observacoes')

        # Nome da unidade de destino
        destino_unidade_nome = None
        if destino_unidade_id:
            cur.execute("SELECT nome, empresa_id FROM unidades WHERE id=?", (destino_unidade_id,))
            unidade_dest = cur.fetchone()
            if unidade_dest:
                destino_unidade_nome = unidade_dest['nome']

        # Inserir movimentacao
        cur.execute("""
            INSERT INTO movimentacoes (equipamento_id, data_movimentacao, tipo_movimento,
                origem_local, origem_unidade, destino_local, destino_unidade, responsavel, observacoes)
            VALUES (?,?,?,?,?,?,?,?,?)
        """, (equip_id, data_mov, tipo_mov,
              equip['local_atual_nome'], equip['unidade_nome'] or equip['local_atual_nome'],
              destino_unidade_nome or "Sem unidade", destino_unidade_nome,
              responsavel, obs))

        # Atualizar equipamento
        cur.execute("""
            UPDATE equipamentos SET unidade_id=?, local_atual_nome=?, cliente_atual=? WHERE id=?
        """, (destino_unidade_id, destino_unidade_nome, None, equip_id))

        db.commit()
        flash("Movimentacao registrada com sucesso!", "success")
        return redirect(url_for('detalhe_equipamento', equip_id=equip_id))

    cur.execute("""
        SELECT e.id as empresa_id, e.nome as empresa_nome, e.tipo as empresa_tipo,
               u.id as unidade_id, u.nome as unidade_nome, u.setor
        FROM empresas e
        LEFT JOIN unidades u ON u.empresa_id = e.id AND u.ativo=1
        WHERE e.ativo=1
        ORDER BY e.tipo DESC, e.nome, u.nome
    """)
    locais = cur.fetchall()

    return render_template('movimentacao_form.html', equip=equip, locais=locais)

@app.route('/locais', methods=['GET', 'POST'])
@login_required
def lista_locais():
    db = get_db()
    cur = db.cursor()

    if request.method == 'POST':
        # Cadastrar nova empresa
        if request.form.get('acao') == 'empresa':
            nome = request.form.get('nome')
            tipo = request.form.get('tipo', 'cliente')
            if nome:
                cur.execute("INSERT INTO empresas (nome, tipo) VALUES (?, ?)", (nome, tipo))
                db.commit()
                flash("Empresa cadastrada com sucesso!", "success")
            return redirect(url_for('lista_locais'))

        # Editar empresa
        if request.form.get('acao') == 'empresa_editar':
            empresa_id = request.form.get('empresa_id')
            nome = request.form.get('nome')
            tipo = request.form.get('tipo', 'cliente')
            if empresa_id and nome:
                cur.execute("UPDATE empresas SET nome=?, tipo=? WHERE id=?", (nome, tipo, empresa_id))
                db.commit()
                flash("Empresa atualizada com sucesso!", "success")
            return redirect(url_for('lista_locais'))

        # Excluir empresa
        if request.form.get('acao') == 'empresa_excluir':
            empresa_id = request.form.get('empresa_id')
            if empresa_id:
                cur.execute("UPDATE empresas SET ativo=0 WHERE id=?", (empresa_id,))
                cur.execute("UPDATE unidades SET ativo=0 WHERE empresa_id=?", (empresa_id,))
                db.commit()
                flash("Empresa excluida com sucesso.", "success")
            return redirect(url_for('lista_locais'))

        # Cadastrar nova unidade
        if request.form.get('acao') == 'unidade':
            empresa_id = request.form.get('empresa_id')
            nome = request.form.get('unidade_nome')
            setor = request.form.get('setor')
            if empresa_id and nome:
                cur.execute("INSERT INTO unidades (empresa_id, nome, setor) VALUES (?, ?, ?)", (empresa_id, nome, setor))
                db.commit()
                flash("Unidade cadastrada com sucesso!", "success")
            return redirect(url_for('lista_locais'))

        # Editar unidade
        if request.form.get('acao') == 'unidade_editar':
            unidade_id = request.form.get('unidade_id')
            nome = request.form.get('unidade_nome')
            setor = request.form.get('setor')
            if unidade_id and nome:
                cur.execute("UPDATE unidades SET nome=?, setor=? WHERE id=?", (nome, setor, unidade_id))
                db.commit()
                flash("Unidade atualizada com sucesso!", "success")
            return redirect(url_for('lista_locais'))

        # Excluir unidade
        if request.form.get('acao') == 'unidade_excluir':
            unidade_id = request.form.get('unidade_id')
            if unidade_id:
                cur.execute("UPDATE unidades SET ativo=0 WHERE id=?", (unidade_id,))
                db.commit()
                flash("Unidade excluida com sucesso.", "success")
            return redirect(url_for('lista_locais'))

    cur.execute("""
        SELECT e.id as empresa_id, e.nome as empresa_nome, e.tipo as empresa_tipo,
               u.id as unidade_id, u.nome as unidade_nome, u.setor
        FROM empresas e
        LEFT JOIN unidades u ON u.empresa_id = e.id AND u.ativo=1
        WHERE e.ativo=1
        ORDER BY e.tipo DESC, e.nome, u.nome
    """)
    locais = cur.fetchall()
    cur.execute("SELECT id, nome, tipo FROM empresas WHERE ativo=1 ORDER BY tipo DESC, nome")
    empresas = cur.fetchall()
    return render_template('locais.html', locais=locais, empresas=empresas)

@app.route('/historico')
@login_required
def historico():
    db = get_db()
    cur = db.cursor()
    
    equip_id = request.args.get('equipamento_id')
    serie = request.args.get('serie')
    
    equip = None
    movimentacoes = []
    sugestoes = []
    
    if equip_id:
        cur.execute("SELECT * FROM equipamentos WHERE id=?", (equip_id,))
        equip = cur.fetchone()
        if equip:
            cur.execute("""
                SELECT m.*, e.modelo, e.numero_serie
                FROM movimentacoes m
                JOIN equipamentos e ON m.equipamento_id = e.id
                WHERE m.equipamento_id = ?
                ORDER BY m.data_movimentacao DESC
            """, (equip_id,))
            movimentacoes = cur.fetchall()
    elif serie:
        cur.execute("SELECT e.*, u.nome as unidade_nome, emp.nome as empresa_nome FROM equipamentos e LEFT JOIN unidades u ON u.id=e.unidade_id LEFT JOIN empresas emp ON emp.id=u.empresa_id WHERE e.ativo=1")
        candidatos = cur.fetchall()
        termos = preparar_termos_busca(serie)
        encontrados = []
        for candidato in candidatos:
            pontuacao = calcular_pontuacao_busca(
                termos,
                candidato["numero_serie"],
                candidato["codigo"],
                candidato["modelo"],
                candidato["fabricante"],
                candidato["local_atual_nome"],
                candidato["cliente_atual"],
                candidato["unidade_nome"],
                candidato["empresa_nome"],
            )
            if pontuacao:
                encontrados.append((pontuacao, candidato))

        encontrados.sort(key=lambda item: item[0], reverse=True)
        # Só aceita resultado se a pontuacao for alta (evita devolver qualquer coisa parecida)
        if encontrados and encontrados[0][0] >= 180:
            equip = encontrados[0][1]
            sugestoes = [item[1] for item in encontrados[1:6]]
            cur.execute("""
                SELECT m.*, e.modelo, e.numero_serie
                FROM movimentacoes m
                JOIN equipamentos e ON m.equipamento_id = e.id
                WHERE m.equipamento_id = ?
                ORDER BY m.data_movimentacao DESC
            """, (equip['id'],))
            movimentacoes = cur.fetchall()
        else:
            equip = None
            sugestoes = []

    return render_template('historico.html', equip=equip, movimentacoes=movimentacoes, serie=serie, sugestoes=sugestoes)

@app.route('/movimentar-equipamento', methods=['GET', 'POST'])
@login_required
def tela_movimentar():
    db = get_db()
    cur = db.cursor()
    busca = request.args.get('q', '')
    tipo = request.args.get('tipo', '')
    sugestoes = []
    equipamento = None

    if request.method == 'POST':
        # Delayed redirect after selection – handled by JS or GET form, but support direct POST too
        equip_id = request.form.get('equipamento_id')
        if equip_id:
            return redirect(url_for('movimentar', equip_id=equip_id))

    sql = """
        SELECT e.*, COALESCE(u.nome, e.local_atual_nome) as local_nome,
               emp.nome as empresa_nome, u.setor as unidade_setor,
               m.ultima_movimentacao
        FROM equipamentos e
        LEFT JOIN unidades u ON e.unidade_id = u.id
        LEFT JOIN empresas emp ON emp.id = u.empresa_id
        LEFT JOIN (
            SELECT equipamento_id, MAX(data_movimentacao) as ultima_movimentacao
            FROM movimentacoes
            WHERE data_movimentacao LIKE '____-__-__'
            GROUP BY equipamento_id
        ) m ON m.equipamento_id = e.id
        WHERE e.ativo=1
    """
    params = []

    if tipo:
        sql += " AND e.tipo_equipamento = ?"
        params.append(tipo)
    sql += " ORDER BY e.tipo_equipamento, e.modelo"

    cur.execute(sql, params)
    equipamentos = cur.fetchall()

    if busca:
        termos = preparar_termos_busca(busca)
        filtrados = []
        for eq in equipamentos:
            pontuacao = calcular_pontuacao_busca(
                termos, eq["codigo"], eq["fabricante"], eq["modelo"],
                eq["numero_serie"], eq["patrimonio"], eq["cliente_atual"],
                eq["local_nome"], eq["empresa_nome"], eq["unidade_setor"],
            )
            if pontuacao >= 180:
                filtrados.append((pontuacao, eq))
        filtrados.sort(key=lambda i: i[0], reverse=True)
        equipamentos = [i[1] for i in filtrados]
        sugestoes = buscar_sugestoes_locais(cur, busca)

    return render_template('tela_movimentar.html',
        equipamentos=equipamentos, busca=busca, filtro_tipo=tipo, sugestoes=sugestoes)


if __name__ == '__main__':
    init_db()
    print("Acesse: http://localhost:5000")
    app.run(debug=True, port=5000)

# Para produção (Render / Gunicorn)
# O banco já existe no deploy, não precisa recriar toda vez
if os.environ.get('RENDER'):
    init_db()
