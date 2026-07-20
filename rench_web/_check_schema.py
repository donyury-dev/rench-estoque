import psycopg2
from urllib.parse import urlparse

url='postgresql://postgres.yfxfmwrasjukbsjjqbzs:kaio82046697@aws-1-us-west-2.pooler.supabase.com:6543/postgres'
r=urlparse(url)
conn=psycopg2.connect(host=r.hostname, port=r.port or 6543, user=r.username, password=r.password, dbname=r.path.lstrip('/'), connect_timeout=10)
cur=conn.cursor()
cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='public' ORDER BY table_name")
for row in cur.fetchall():
    print(row[0])
cur.execute("""SELECT column_name, data_type FROM information_schema.columns WHERE table_name='equipamentos' ORDER BY ordinal_position""")
for row in cur.fetchall():
    print(row)
cur.close()
conn.close()
