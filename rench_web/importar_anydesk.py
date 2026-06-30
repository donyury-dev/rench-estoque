import sqlite3
import pandas as pd
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'rench_web.db')
EXCEL_PATH = r'C:\Users\Kaio\Downloads\AnyDesk_Severs.xlsx'

db = sqlite3.connect(DB_PATH)
cur = db.cursor()

df = pd.read_excel(EXCEL_PATH)
count = 0
for _, row in df.iterrows():
    local = str(row['Local']).strip() if pd.notna(row['Local']) else None
    anydesk = str(row['AnyDesk']).strip() if pd.notna(row['AnyDesk']) else None
    senha = str(row['Senha']).strip() if pd.notna(row['Senha']) else None
    if local and anydesk:
        cur.execute("""
            INSERT INTO acesso_remoto (local, anydesk, senha, observacoes)
            VALUES (?, ?, ?, ?)
        """, (local, anydesk, senha, 'Importado da planilha'))
        count += 1

db.commit()
print(f'{count} acessos remotos importados com sucesso!')

cur.execute("SELECT COUNT(*) FROM acesso_remoto WHERE ativo=1")
print('Total no banco:', cur.fetchone()[0])
db.close()
