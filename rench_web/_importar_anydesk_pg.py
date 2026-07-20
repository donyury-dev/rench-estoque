import pandas as pd
import app as appmod

EXCEL_PATH = r'C:\Users\Kaio\Downloads\AnyDesk_Severs.xlsx'

df = pd.read_excel(EXCEL_PATH)

with appmod.app.app_context():
    db = appmod.get_db()
    cur = db.cursor()

    cur.execute("SELECT COUNT(*) as c FROM acesso_remoto")
    existentes = cur.fetchone()['c']
    print('Registros ja existentes antes de importar:', existentes)

    count = 0
    for _, row in df.iterrows():
        local = str(row['Local']).strip() if pd.notna(row['Local']) else None
        anydesk = str(row['AnyDesk']).strip() if pd.notna(row['AnyDesk']) else None
        senha = str(row['Senha']).strip() if pd.notna(row['Senha']) else None
        if local and anydesk:
            cur.execute("""
                INSERT INTO acesso_remoto (local, anydesk, senha, observacoes)
                VALUES (%s, %s, %s, %s)
            """, (local, anydesk, senha, 'Importado da planilha'))
            count += 1

    db.commit()
    print(f'{count} acessos remotos importados com sucesso!')

    cur.execute("SELECT COUNT(*) as c FROM acesso_remoto WHERE ativo=1")
    print('Total no banco agora:', cur.fetchone()['c'])
