# -*- coding: utf-8 -*-
import sqlite3
conn = sqlite3.connect('rench_web.db')
cur = conn.cursor()

def get_id(nome):
    cur.execute("SELECT id FROM empresas WHERE nome=?", (nome,))
    r = cur.fetchone()
    return r[0] if r else None

samir_id = get_id('SAMIR')
id4id = get_id('4ID')
csi_id = get_id('CSI')

if csi_id:
    # Hosp de Francsico Morato -> Samir (corrige tambem o nome)
    cur.execute("UPDATE unidades SET empresa_id=?, nome=? WHERE empresa_id=? AND nome=?",
                (samir_id, 'Hospital de Francisco Morato', csi_id, 'Hosp de Francsico Morato'))
    # cs24hrs e CSI 24hrs -> 4ID
    cur.execute("UPDATE unidades SET empresa_id=? WHERE empresa_id=? AND nome='cs24hrs'", (id4id, csi_id))
    cur.execute("UPDATE unidades SET empresa_id=? WHERE empresa_id=? AND nome='CSI 24hrs'", (id4id, csi_id))
    # Confirma que nao sobrou nenhuma unidade em CSI
    cur.execute("SELECT COUNT(*) FROM unidades WHERE empresa_id=?", (csi_id,))
    restante = cur.fetchone()[0]
    print('Unidades restantes em CSI:', restante)
    if restante == 0:
        cur.execute("DELETE FROM empresas WHERE id=?", (csi_id,))
        print('Empresa CSI removida.')
    conn.commit()
else:
    print('CSI ja nao existe.')

cur.execute("SELECT id, nome, tipo FROM empresas ORDER BY tipo DESC, nome")
print('EMPRESAS FINAIS:')
for row in cur.fetchall():
    print(' ', row)

cur.execute("SELECT u.nome FROM unidades u JOIN empresas e ON e.id=u.empresa_id WHERE e.nome='SAMIR' AND u.nome LIKE '%Morato%'")
print('Verificacao Samir Morato:', cur.fetchall())
cur.execute("SELECT u.nome FROM unidades u JOIN empresas e ON e.id=u.empresa_id WHERE e.nome='4ID'")
print('Verificacao unidades 4ID:', cur.fetchall())
conn.close()
