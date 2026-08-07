"""
Script de correcao para itens de estoque que foram renomeados
indevidamente, como 'Drum R10' e 'Drum OkiData'.

Converte o tipo_suprimento de volta para 'Drum Black' e define
a marca correta (R10 ou OKIData), propagando a alteracao para
as entregas vinculadas.
"""
import os
import sys
import psycopg2
import psycopg2.extras
from urllib.parse import urlparse

# Adiciona o diretorio do app no path para reutilizar funcoes
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

CORRECOES = [
    # (tipo_antigo, modelo_antigo, marca_antiga, tipo_novo, modelo_novo, marca_nova)
    ('Drum R10', 'ES5112/4172', '', 'Drum Black', 'ES5112/4172', 'R10'),
    ('Drum OkiData', 'ES5112/4172', '', 'Drum Black', 'ES5112/4172', 'OKIData'),
    ('Drum OKIData', 'ES5112/4172', '', 'Drum Black', 'ES5112/4172', 'OKIData'),
]

def main():
    db = get_db()
    cur = db.cursor()

    for old_tipo, old_modelo, old_marca, new_tipo, new_modelo, new_marca in CORRECOES:
        old_marca_sql = old_marca or ''
        new_marca_sql = new_marca or None

        # Verifica se existe item no estoque com os dados antigos
        cur.execute("""
            SELECT id, quantidade FROM estoque
            WHERE tipo_suprimento=%s AND modelo_impressora=%s AND COALESCE(marca, '')=%s
        """, (old_tipo, old_modelo, old_marca_sql))
        itens_antigos = cur.fetchall()

        if not itens_antigos:
            print(f'Nenhum item antigo encontrado: {old_tipo} {old_modelo} ({old_marca})')
            continue

        for item in itens_antigos:
            print(f'Corrigindo estoque id={item["id"]}: {old_tipo} {old_modelo} ({old_marca}) -> {new_tipo} {new_modelo} ({new_marca})')

            # Verifica se ja existe o item de destino
            cur.execute("""
                SELECT id FROM estoque
                WHERE tipo_suprimento=%s AND modelo_impressora=%s AND COALESCE(marca, '')=%s
            """, (new_tipo, new_modelo, new_marca or ''))
            destino = cur.fetchone()

            if destino:
                # Consolida o saldo no item existente
                print(f'  Consolidando saldo {item["quantidade"]} no estoque id={destino["id"]}')
                cur.execute("""
                    UPDATE estoque SET quantidade = quantidade + %s WHERE id = %s
                """, (item['quantidade'], destino['id']))
                cur.execute("""
                    UPDATE estoque_movimentacoes SET estoque_id = %s WHERE estoque_id = %s
                """, (destino['id'], item['id']))
                cur.execute("DELETE FROM estoque WHERE id = %s", (item['id'],))
            else:
                # Apenas renomeia o item
                cur.execute("""
                    UPDATE estoque
                    SET tipo_suprimento=%s, modelo_impressora=%s, marca=%s
                    WHERE id=%s
                """, (new_tipo, new_modelo, new_marca_sql, item['id']))

            # Propaga a alteracao nas entregas
            cur.execute("""
                UPDATE suprimentos_itens
                SET tipo_suprimento=%s, modelo_impressora=%s, marca=%s
                WHERE tipo_suprimento=%s AND modelo_impressora=%s AND COALESCE(marca, '')=%s
            """, (new_tipo, new_modelo, new_marca_sql, old_tipo, old_modelo, old_marca_sql))
            print(f'  {cur.rowcount} registro(s) de entrega atualizado(s)')

    db.commit()
    cur.close()
    db.close()
    print('Correcao concluida.')

if __name__ == '__main__':
    main()
