# -*- coding: utf-8 -*-
"""
migrar_historico_defeitos.py
============================
"""
import os
import sqlite3
from sqlalchemy import create_engine, text

DATABASE_URL = os.environ["DATABASE_URL"]
engine = create_engine(DATABASE_URL, pool_pre_ping=True)

sqlite_conn = sqlite3.connect('rench_web.db')
sqlite_conn.row_factory = sqlite3.Row
sqlite_cur = sqlite_conn.cursor()

columns = ['id','equipamento_id','descricao','data_ocorrencia']
sqlite_cur.execute(f"SELECT {','.join(columns)} FROM historico_defeitos")
rows = sqlite_cur.fetchall()

if rows:
    placeholders = ','.join([f':{c}' for c in columns])
    with engine.connect() as conn:
        conn.execute(
            text(f"INSERT INTO historico_defeitos ({','.join(columns)}) VALUES ({placeholders})"),
            [dict(r) for r in rows]
        )
        conn.commit()
print(f"Historico_defeitos: {len(rows)} OK")
sqlite_conn.close()
