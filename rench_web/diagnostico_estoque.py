"""
Script de diagnostico para verificar itens de estoque do tipo Drum
no modelo ES5112/4172 e entregas vinculadas.
"""
import os
import sys
import psycopg2
import psycopg2.extras
from urllib.parse import urlparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def get_db():
    database_url = os.environ.get('DATABASE_URL')
    if not database_url:
        raise RuntimeError('DATABASE_URL nao configurada')
    parsed = urlparse(database_url)
    conn = psycopg2.connect(
        host=parsed.hostname,
        port=parsed.port or 5432,
        dbname=parsed.path.lstrip('/'),
        user=parsed.username,
        password=parsed.password
    )
    conn.cursor_factory = psycopg2.extras.RealDictCursor
    return conn

def main():
    db = get_db()
    cur = db.cursor()

    print('=== ITENS DE ESTOQUE DO MODELO ES5112/4172 ===')
    cur.execute("""
        SELECT id, tipo_suprimento, modelo_impressora, marca, quantidade
        FROM estoque
        WHERE modelo_impressora = 'ES5112/4172'
        ORDER BY tipo_suprimento, marca
    """)
    rows = cur.fetchall()
    for r in rows:
        print(f"id={r['id']} | {r['tipo_suprimento']} | marca={r['marca'] or '-'} | qtd={r['quantidade']}")

    print('\n=== TODOS OS ITENS DE ESTOQUE ( Drum ) ===')
    cur.execute("""
        SELECT id, tipo_suprimento, modelo_impressora, marca, quantidade
        FROM estoque
        WHERE tipo_suprimento ILIKE '%drum%'
        ORDER BY tipo_suprimento, modelo_impressora, marca
    """)
    for r in cur.fetchall():
        print(f"id={r['id']} | {r['tipo_suprimento']} | {r['modelo_impressora']} | marca={r['marca'] or '-'} | qtd={r['quantidade']}")

    print('\n=== ULTIMAS ENTREGAS COM DRUM ES5112/4172 ===')
    cur.execute("""
        SELECT si.id, si.tipo_suprimento, si.modelo_impressora, si.marca, si.quantidade, s.data_entrega, u.nome as unidade
        FROM suprimentos_itens si
        JOIN suprimentos s ON si.suprimento_id = s.id
        JOIN unidades u ON s.unidade_id = u.id
        WHERE si.modelo_impressora = 'ES5112/4172'
        ORDER BY s.data_entrega DESC
        LIMIT 20
    """)
    for r in cur.fetchall():
        print(f"{r['tipo_suprimento']} | marca={r['marca'] or '-'} | qtd={r['quantidade']} | {r['data_entrega']} | {r['unidade']}")

    cur.close()
    db.close()

if __name__ == '__main__':
    main()
