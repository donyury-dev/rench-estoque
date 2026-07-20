# -*- coding: utf-8 -*-
"""
migrar_para_postgres.py
=======================
Cria as tabelas no Supabase e migra todos os dados do SQLite local.
"""
import sqlite3
from sqlalchemy import create_engine, text

DATABASE_URL = "postgresql://postgres.yfxfmwrasjukbsjjqbzs:kaio82046697@aws-1-us-west-2.pooler.supabase.com:6543/postgres"

engine = create_engine(DATABASE_URL, pool_pre_ping=True)

# Schema SQL compatível com PostgreSQL
SCHEMA = """
DROP TABLE IF EXISTS historico_defeitos CASCADE;
DROP TABLE IF EXISTS movimentacoes CASCADE;
DROP TABLE IF EXISTS equipamentos CASCADE;
DROP TABLE IF EXISTS unidades CASCADE;
DROP TABLE IF EXISTS empresas CASCADE;

CREATE TABLE empresas (
    id SERIAL PRIMARY KEY,
    nome VARCHAR(255) NOT NULL,
    tipo VARCHAR(50) NOT NULL,
    ativo INTEGER DEFAULT 1
);

CREATE TABLE unidades (
    id SERIAL PRIMARY KEY,
    empresa_id INTEGER NOT NULL REFERENCES empresas(id),
    nome VARCHAR(255) NOT NULL,
    setor TEXT,
    ativo INTEGER DEFAULT 1
);

CREATE TABLE equipamentos (
    id SERIAL PRIMARY KEY,
    codigo VARCHAR(100),
    tipo_equipamento VARCHAR(100),
    fabricante VARCHAR(255),
    modelo VARCHAR(255),
    numero_serie VARCHAR(255),
    patrimonio VARCHAR(255),
    status VARCHAR(100),
    unidade_id INTEGER REFERENCES unidades(id),
    local_atual_nome VARCHAR(255),
    cliente_atual VARCHAR(255),
    observacoes TEXT,
    contador_mono INTEGER DEFAULT 0,
    contador_color INTEGER DEFAULT 0,
    data_cadastro VARCHAR(50),
    ativo INTEGER DEFAULT 1
);

CREATE TABLE movimentacoes (
    id SERIAL PRIMARY KEY,
    equipamento_id INTEGER NOT NULL REFERENCES equipamentos(id),
    data_movimentacao VARCHAR(50) NOT NULL,
    origem_local VARCHAR(255),
    origem_unidade VARCHAR(255),
    destino_local VARCHAR(255) NOT NULL,
    destino_unidade VARCHAR(255),
    tipo_movimento VARCHAR(100) NOT NULL,
    responsavel VARCHAR(255),
    observacoes TEXT,
    contador_mono_anterior INTEGER,
    contador_mono_novo INTEGER,
    contador_color_anterior INTEGER,
    contador_color_novo INTEGER
);

CREATE TABLE historico_defeitos (
    id SERIAL PRIMARY KEY,
    equipamento_id INTEGER NOT NULL REFERENCES equipamentos(id),
    descricao TEXT,
    data_ocorrencia VARCHAR(50)
);
"""

print("Criando tabelas no PostgreSQL...")
with engine.connect() as conn:
    conn.execute(text(SCHEMA))
    conn.commit()

# Migra dados
print("Lendo dados do SQLite...")
sqlite_conn = sqlite3.connect('rench_web.db')
sqlite_conn.row_factory = sqlite3.Row
sqlite_cur = sqlite_conn.cursor()

def migrate_table(table, columns):
    sqlite_cur.execute(f"SELECT {','.join(columns)} FROM {table}")
    rows = sqlite_cur.fetchall()
    if not rows:
        print(f"  {table}: 0 registros")
        return
    placeholders = ','.join([f':{c}' for c in columns])
    with engine.connect() as conn:
        conn.execute(text(f"TRUNCATE TABLE {table} RESTART IDENTITY CASCADE"))
        conn.execute(
            text(f"INSERT INTO {table} ({','.join(columns)}) VALUES ({placeholders})"),
            [dict(r) for r in rows]
        )
        conn.commit()
    print(f"  {table}: {len(rows)} registros migrados")

migrate_table('empresas', ['id','nome','tipo','ativo'])
migrate_table('unidades', ['id','empresa_id','nome','setor','ativo'])
migrate_table('equipamentos', ['id','codigo','tipo_equipamento','fabricante','modelo','numero_serie','patrimonio','status','unidade_id','local_atual_nome','cliente_atual','observacoes','contador_mono','contador_color','data_cadastro','ativo'])
migrate_table('movimentacoes', ['id','equipamento_id','data_movimentacao','origem_local','origem_unidade','destino_local','destino_unidade','tipo_movimento','responsavel','observacoes','contador_mono_anterior','contador_mono_novo','contador_color_anterior','contador_color_novo'])
migrate_table('historico_defeitos', ['id','equipamento_id','descricao','data_ocorrencia'])

sqlite_conn.close()
print("MIGRACAO CONCLUIDA")
