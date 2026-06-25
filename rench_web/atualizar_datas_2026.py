import sqlite3
import os

db_path = os.path.join(os.path.dirname(__file__), 'rench_web.db')
db = sqlite3.connect(db_path)
cur = db.cursor()
cur.execute("""UPDATE movimentacoes SET data_movimentacao = '2026-' || substr(data_movimentacao, 6, 5) WHERE data_movimentacao LIKE '____-__-__'""")
print('Movimentacoes atualizadas:', cur.rowcount)
db.commit()

cur.execute("""SELECT substr(data_movimentacao, 1, 4) as ano, count(*) FROM movimentacoes WHERE data_movimentacao LIKE '____-__-__' GROUP BY ano ORDER BY ano""")
print(cur.fetchall())
db.close()
