import app as appmod

TABELAS = ['empresas', 'unidades', 'equipamentos', 'movimentacoes', 'historico_defeitos', 'acesso_remoto']

with appmod.app.app_context():
    db = appmod.get_db()
    cur = db.cursor()
    for t in TABELAS:
        try:
            cur.execute(f"SELECT setval('{t}_id_seq', COALESCE((SELECT MAX(id) FROM {t}), 1))")
            novo = cur.fetchone()
            print(f"{t}: sequencia ajustada para {novo}")
        except Exception as e:
            print(f"{t}: erro -> {e}")
            db.rollback()
    db.commit()
    print("OK - todas as sequencias corrigidas e commitadas.")
