from sqlalchemy import create_engine, text
DATABASE_URL = 'postgresql://postgres.yfxfmwrasjukbsjjqbzs:kaio82046697@aws-1-us-west-2.pooler.supabase.com:6543/postgres'
engine = create_engine(DATABASE_URL)
with engine.connect() as conn:
    for t in ['empresas','unidades','equipamentos','movimentacoes','historico_defeitos']:
        r = conn.execute(text(f'SELECT COUNT(*) FROM {t}')).fetchone()
        print(t, r[0])
