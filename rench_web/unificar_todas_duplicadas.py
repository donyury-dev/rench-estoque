# -*- coding: utf-8 -*-
import sqlite3, unicodedata, re
from collections import defaultdict

conn = sqlite3.connect('rench_web.db')
conn.text_factory = str
cur = conn.cursor()

def norm(s):
    s = ''.join(c for c in unicodedata.normalize('NFD', str(s)) if unicodedata.category(c)!='Mn')
    s = s.upper()
    s = re.sub(r'[^A-Z0-9 ]',' ',s)
    s = re.sub(r'\s+',' ',s).strip()
    return s

cur.execute('SELECT id, nome, empresa_id, ativo FROM unidades WHERE ativo=1 ORDER BY empresa_id, id')
unidades = cur.fetchall()

# Agrupa por nome normalizado dentro da mesma empresa
grupos = defaultdict(list)
for uid, nome, eid, ativo in unidades:
    grupos[(norm(nome), eid)].append((uid, nome))

removidas = 0
for (nome_norm, eid), items in grupos.items():
    if len(items) > 1:
        manter_id = items[0][0]
        for remover_id, _ in items[1:]:
            # Atualiza equipamentos
            cur.execute("UPDATE equipamentos SET unidade_id=? WHERE unidade_id=?", (manter_id, remover_id))
            # Tenta atualizar local_atual_nome se bater exatamente com o nome antigo
            cur.execute("SELECT nome FROM unidades WHERE id=?", (remover_id,))
            nome_remover = cur.fetchone()[0]
            cur.execute("SELECT nome FROM unidades WHERE id=?", (manter_id,))
            nome_manter = cur.fetchone()[0]
            cur.execute("UPDATE equipamentos SET local_atual_nome=? WHERE local_atual_nome=?", (nome_manter, nome_remover))
            cur.execute("UPDATE unidades SET ativo=0 WHERE id=?", (remover_id,))
            removidas += 1
            print(f'Unificada: manter={manter_id} ({nome_manter}), remover={remover_id} ({nome_remover}), empresa={eid}')

conn.commit()
conn.close()
print(f'Total de unidades duplicadas removidas: {removidas}')
