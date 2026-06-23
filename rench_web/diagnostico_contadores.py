import sqlite3, openpyxl

wb = openpyxl.load_workbook("../data_atual.xlsx", data_only=True)
ws = wb["IMPRESSORA"]
planilha = {}
for i,row in enumerate(ws.iter_rows(min_row=2, values_only=True), start=2):
    s = row[2]
    c = row[3]
    if s and c:
        ch = str(s).upper().strip().lstrip(" \t")
        if ch not in planilha: planilha[ch]=[]
        planilha[ch].append(i)
wb.close()

con = sqlite3.connect("rench_web.db")
cur = con.cursor()
banco = {}
for id,ns in cur.execute("SELECT id, numero_serie FROM equipamentos WHERE tipo_equipamento='impressora'").fetchall():
    if ns:
        ch = str(ns).upper().strip().lstrip(" \t")
        if ch not in banco: banco[ch]=[]
        banco[ch].append(id)

for serie in ('AK5C034556','BRBSP9D0XT','AK76023968'):
    print(serie, "planilha:", serie in planilha, "banco:", serie in banco)

pk = set(planilha.keys())
bk = set(banco.keys())
print("uniq planilha:", len(pk), "uniq banco:", len(bk), "comum:", len(pk & bk), "só planilha:", len(pk-bk), "só banco:", len(bk-pk))

# Mostrar exemplos de séries no banco que não estão na planilha
print("Exemplos só banco:", sorted(list(bk - pk))[:10])
print("Exemplos só planilha:", sorted(list(pk - bk))[:10])

# Contador atual CNCRNBJ43Y
r = cur.execute("SELECT numero_serie, contador_mono, contador_color FROM equipamentos WHERE UPPER(numero_serie)=?",("CNCRNBJ43Y",)).fetchone()
print("cncrnbj43y final:", r)

# Total stats
t = cur.execute("SELECT COUNT(*) FROM equipamentos WHERE tipo_equipamento='impressora'").fetchone()[0]
z = cur.execute("SELECT COUNT(*) FROM equipamentos WHERE tipo_equipamento='impressora' AND (contador_mono IS NULL OR contador_mono=0) AND (contador_color IS NULL OR contador_color=0)").fetchone()[0]
print("Total impressoras:", t, "Zeradas:", z)
con.close()
