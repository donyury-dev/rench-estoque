# -*- coding: utf-8 -*-
"""
migrar_movimentacoes.py
=======================
Migra apenas a tabela movimentacoes em lotes pequenos (o servidor fechou conexao no lote grande).
"""
import sqlite3
from sqlalchemy import create_engine, text

DATABASE_URL = "postgresql://postgres.yfxfmwrasjukbsjjqbzs:kaio82046697@aws-1-us-west-2.pooler.supabase.com:6543/postgres"
engine = create_engine(DATABASE_URL, pool_pre_ping=True)

sqlite_conn = sqlite3.connect('rench_web.db')
sqlite_conn.row_factory = sqlite3.Row
sqlite_cur = sqlite_conn.cursor()

columns = ['id','equipamento_id','data_movimentacao','origem_local','origem_unidade','destino_local','destino_unidade','tipo_movimento','responsavel','observacoes','contador_mono_anterior','contador_mono_novo','contador_color_anterior','contador_color_novo']
sqlite_cur.execute(f"SELECT {','.join(columns)} FROM movimentacoes")
rows = sqlite_cur.fetchall()

placeholders = ','.join([f':{c}' for c in columns])

print(f"Movimentacoes para migrar: {len(rows)}")
BATCH = 100
for i in range(0, len(rows), BATCH):
    batch = rows[i:i+BATCH]
    with engine.connect() as conn:
        conn.execute(
            text(f"INSERT INTO movimentacoes ({','.join(columns)}) VALUES ({placeholders})"),
            [dict(r) for r in batch]
        )
        conn.commit()
    print(f"  migrados {i+len(batch)}/{len(rows)}")

sqlite_conn.close()
print("OK")
