# -*- coding: utf-8 -*-
import sqlite3, re
import pandas as pd

path = r'C:\Users\Kaio\Downloads\RELACAO UNIDADES ANTIGA GRUPO SAMIR.xlsx'
df = pd.read_excel(path, header=2).dropna(how='all').reset_index(drop=True)

PREFIXES = {'PA','PS','PU','HD','HM','UBS','UPA','USF','AME','STA','UND','URSI'}
CONNECT = {'DE','DA','DO','DAS','DOS','E'}

def title_case_pt(name):
    words = str(name).split()
    out = []
    for i, w in enumerate(words):
        wu = w.upper()
        if i == 0 and wu in PREFIXES:
            out.append(wu)
        elif i != 0 and wu in CONNECT:
            out.append(wu.lower())
        else:
            out.append(w.capitalize())
    return ' '.join(out)

canon = []
for _, row in df.iterrows():
    nome = str(row['UNIDADE']).strip()
    endereco = '' if pd.isna(row['ENDERE\u00c7O']) else str(row['ENDERE\u00c7O']).strip()
    numero = row['NUMERO']
    numero = '' if pd.isna(numero) else str(int(numero))
    cidade = '' if pd.isna(row['CIDADE']) else str(row['CIDADE']).strip()
    estado = '' if pd.isna(row['ESTADO']) else str(row['ESTADO']).strip()
    canon.append({'nome': nome, 'endereco': endereco, 'numero': numero, 'cidade': cidade, 'estado': estado})

def build_setor(c):
    end = c['endereco']
    if c['numero']:
        end = f"{end}, {c['numero']}" if end else c['numero']
    cidade_uf = f"{c['cidade']}/{c['estado']}" if c['cidade'] else ''
    if end and cidade_uf:
        return f"{end} - {cidade_uf}"
    return end or cidade_uf

# Mapa manual: unidade_id_sistema -> (indice_canon, sufixo)
MAPA = {
    150:(9,''), 97:(36,''), 93:(36,''), 111:(36,' (B)'), 110:(36,' (P)'),
    17:(47,''), 145:(47,''), 168:(11,''), 47:(11,' (Capela do Socorro - D.O)'),
    66:(11,' (Capela do Socorro - US)'), 120:(38,''), 77:(54,''), 69:(13,''),
    197:(13,''), 27:(45,''), 148:(4,''), 89:(18,' (B)'), 88:(18,' (P)'),
    48:(7,''), 188:(7,''), 174:(30,''), 178:(30,' - RX'), 179:(30,' - Laudo'),
    180:(30,' - Backup'), 151:(5,''), 170:(44,''), 107:(44,''), 52:(3,''),
    103:(19,''), 135:(19,''), 184:(34,''), 40:(34,''), 3:(0,''), 2:(1,''),
    154:(52,''), 26:(37,''), 38:(33,''), 143:(50,''), 44:(53,''), 34:(55,''),
    166:(58,''), 114:(58,''), 196:(58,''), 96:(58,' - Teste Ergom\u00e9trico'),
    106:(56,''), 187:(56,' - Sala Nova de RX'), 109:(22,''), 32:(22,''),
    131:(21,''), 129:(21,''), 162:(20,' (B)'), 80:(20,' (P)'), 119:(24,''),
    160:(6,''), 113:(6,''), 130:(16,''), 137:(29,' (B)'), 68:(29,' (P)'),
    24:(14,''), 116:(25,''), 142:(23,''), 136:(23,''), 7:(12,''),
    115:(31,' - BK'), 54:(31,' - P'), 175:(26,''), 83:(26,''), 182:(41,''),
    5:(41,' (B)'), 46:(41,' (P)'), 33:(17,''), 153:(46,''), 147:(28,''),
    41:(28,' - BK'), 56:(28,' - L'), 87:(28,' - P'), 94:(27,''), 82:(43,''),
    70:(32,''),
}

conn = sqlite3.connect('rench_web.db')
conn.text_factory = str
cur = conn.cursor()

log = []
for uid, (idx, suf) in MAPA.items():
    c = canon[idx]
    novo_nome = title_case_pt(c['nome']) + suf
    novo_setor = build_setor(c)
    cur.execute("SELECT nome, setor FROM unidades WHERE id=?", (uid,))
    r = cur.fetchone()
    if not r:
        log.append(f"AVISO: id={uid} nao encontrado no banco!")
        continue
    antigo_nome, antigo_setor = r
    cur.execute("UPDATE unidades SET nome=?, setor=? WHERE id=?", (novo_nome, novo_setor, uid))
    log.append(f"id={uid:4} | '{antigo_nome}' -> '{novo_nome}' | setor: '{novo_setor}'")

conn.commit()
conn.close()

with open('_update_log.txt', 'w', encoding='utf-8') as f:
    f.write('\n'.join(log))
print('Total atualizados:', len(MAPA))
