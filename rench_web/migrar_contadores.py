# -*- coding: utf-8 -*-
import sqlite3
conn = sqlite3.connect('rench_web.db')
cur = conn.cursor()

# Adiciona as colunas de contador na tabela movimentacoes
for col in ['contador_mono_anterior','contador_mono_novo','contador_color_anterior','contador_color_novo']:
    try:
        cur.execute(f"ALTER TABLE movimentacoes ADD COLUMN {col} INTEGER")
        print(f'Coluna {col} adicionada.')
    except sqlite3.OperationalError as e:
        print(f'Coluna {col}: {e}')

conn.commit()
conn.close()
print('OK')
