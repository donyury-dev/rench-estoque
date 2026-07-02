# -*- coding: utf-8 -*-
import sqlite3

conn = sqlite3.connect('rench_web.db')
cur = conn.cursor()

SAMIR_ID = 4

# 1) Criar empresa "4ID" (cliente) e mover CDI + Pronto Socorro para ela
cur.execute("SELECT id FROM empresas WHERE nome='4ID'")
row = cur.fetchone()
if row:
    quatro_id = row[0]
else:
    cur.execute("INSERT INTO empresas (nome, tipo, ativo) VALUES ('4ID', 'cliente', 1)")
    quatro_id = cur.lastrowid

cur.execute("UPDATE unidades SET empresa_id=? WHERE id=157", (quatro_id,))  # CDI - Suzano 4ID
cur.execute("UPDATE unidades SET nome='CDI Suzano' WHERE id=157")
cur.execute("UPDATE unidades SET empresa_id=? WHERE id=167", (quatro_id,))  # Pronto Socorro Central de Praia Grande
cur.execute("DELETE FROM empresas WHERE id IN (47, 50)")  # CDI, Pronto Socorro (vazias agora)

# 2) CAT: nao existe. Equipamentos com local_atual_nome='CAT' passam para 'R10 - SP'
cur.execute("UPDATE equipamentos SET local_atual_nome='R10 - SP' WHERE local_atual_nome='CAT'")
cur.execute("UPDATE unidades SET empresa_id=? WHERE id=26", (SAMIR_ID,))  # Miracatu -> Samir
cur.execute("DELETE FROM unidades WHERE id=6")   # unidade fake "CAT"
cur.execute("DELETE FROM empresas WHERE id=5")   # empresa fake "CAT"

# 3) Renomear clientes reais mantidos
cur.execute("UPDATE empresas SET nome='Humana Magna' WHERE id=8")
cur.execute("UPDATE empresas SET nome='Stuttgart Porsche' WHERE id=9")
cur.execute("DELETE FROM unidades WHERE id=203")  # unidade duplicada "Stuttgart Porsche" dentro do proprio Porsche
cur.execute("UPDATE empresas SET tipo='fornecedor' WHERE id=16")  # Micnet -> fornecedor

# 4) Mesclar todas essas "empresas" (na verdade unidades da Samir) para dentro da Samir
merge_to_samir_ids = [1,2,6,7,12,14,15,18,19,20,21,22,23,24,25,26,27,28,29,30,31,32,33,
                       35,36,37,38,39,40,41,42,43,44,45,46,48,49,51,52,53,54]
for eid in merge_to_samir_ids:
    cur.execute("UPDATE unidades SET empresa_id=? WHERE empresa_id=?", (SAMIR_ID, eid))

# Ajustes de nome pedidos pelo usuario
cur.execute("UPDATE unidades SET nome='Hospital Juquitiba' WHERE id=33")     # Juquitiba
cur.execute("UPDATE unidades SET nome='Hospital Nova Odessa' WHERE id=119") # Nova Odessa
cur.execute("UPDATE unidades SET nome='Ama São Luiz' WHERE id=148")         # São Luis
cur.execute("UPDATE unidades SET nome='Ama Parque Fernanda' WHERE id=151") # Pq Fernanda
cur.execute("UPDATE unidades SET nome='Ama Jd Angela' WHERE id=154")       # JD Angela

# Apagar as empresas-fachada que ja estao vazias
cur.execute("DELETE FROM empresas WHERE id IN (%s)" % ",".join(str(x) for x in merge_to_samir_ids))

conn.commit()

# Conferencia final
print("=== EMPRESAS RESTANTES ===")
cur.execute("SELECT id, nome, tipo FROM empresas ORDER BY tipo DESC, nome")
for r in cur.fetchall():
    print(r)

cur.execute("SELECT COUNT(*) FROM unidades WHERE empresa_id NOT IN (SELECT id FROM empresas)")
print("\nunidades orfas (deveria ser 0):", cur.fetchone()[0])

cur.execute("SELECT COUNT(*) FROM unidades WHERE empresa_id=?", (SAMIR_ID,))
print("total unidades agora sob Samir:", cur.fetchone()[0])

conn.close()
print("\nMIGRACAO CONCLUIDA COM SUCESSO")
