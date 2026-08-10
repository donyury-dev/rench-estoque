"""
Ajusta manualmente o saldo de um item de estoque, registrando a movimentacao.

Uso:
    python ajustar_saldo.py <estoque_id> <nova_quantidade> "<motivo>"

Exemplo:
    python ajustar_saldo.py 519 3 "Correcao de saldo fantasma"

Para listar os ids disponiveis:
    python ajustar_saldo.py --listar
"""
import os
import sys
import psycopg2
import psycopg2.extras
from urllib.parse import urlparse


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


def listar(cur):
    cur.execute("""
        SELECT id, tipo_suprimento, modelo_impressora, marca, quantidade
        FROM estoque
        ORDER BY modelo_impressora, tipo_suprimento, marca
    """)
    print(f"{'ID':>5} | {'SUPRIMENTO':<32} | {'MODELO':<16} | {'MARCA':<9} | QTD")
    print('-' * 80)
    for r in cur.fetchall():
        print(f"{r['id']:>5} | {r['tipo_suprimento']:<32} | {r['modelo_impressora']:<16} | {(r['marca'] or '-'):<9} | {r['quantidade']}")


def ajustar(db, cur, estoque_id, nova_qtd, motivo):
    cur.execute("SELECT id, tipo_suprimento, modelo_impressora, marca, quantidade FROM estoque WHERE id=%s", (estoque_id,))
    item = cur.fetchone()
    if not item:
        print(f'Item id={estoque_id} nao encontrado.')
        return

    saldo_antes = int(item['quantidade'] or 0)
    diferenca = nova_qtd - saldo_antes

    nome = f"{item['tipo_suprimento']} {item['modelo_impressora']}"
    if item['marca']:
        nome += f" ({item['marca']})"

    print(f'Item: {nome}')
    print(f'Saldo atual: {saldo_antes} -> novo saldo: {nova_qtd} (diferenca {diferenca:+d})')

    cur.execute("UPDATE estoque SET quantidade=%s, data_atualizacao=CURRENT_TIMESTAMP WHERE id=%s", (nova_qtd, estoque_id))
    cur.execute("""
        INSERT INTO estoque_movimentacoes
            (estoque_id, tipo_movimento, quantidade, saldo_antes, saldo_depois, motivo, responsavel, data_movimento)
        VALUES (%s, 'ajuste', %s, %s, %s, %s, 'script', CURRENT_TIMESTAMP)
    """, (estoque_id, diferenca, saldo_antes, nova_qtd, motivo))
    db.commit()
    print('Saldo ajustado com sucesso.')


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return

    db = get_db()
    cur = db.cursor()

    if sys.argv[1] == '--listar':
        listar(cur)
    elif len(sys.argv) >= 3:
        estoque_id = int(sys.argv[1])
        nova_qtd = int(sys.argv[2])
        motivo = sys.argv[3] if len(sys.argv) > 3 else 'Ajuste manual via script'
        ajustar(db, cur, estoque_id, nova_qtd, motivo)
    else:
        print(__doc__)

    cur.close()
    db.close()


if __name__ == '__main__':
    main()
