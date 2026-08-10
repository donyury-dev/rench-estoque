# -*- coding: utf-8 -*-
"""Corrige definitivamente as Drums do modelo ES5112/4172.

Causa raiz (ja corrigida em app.py): _normalizar_modelos_estoque() agrupava os
itens apenas por tipo_suprimento, ignorando a marca. Isso fundia
'Drum Black + R10' com 'Drum Black + OKIData' em uma unica linha a cada
inicializacao do app, somando os saldos e apagando uma das linhas.

Estado correto informado pelo responsavel:
    Drum R10     = 3   (corresponde a entrada 'Voltou do concerto +3' do Kaio)
    Drum OkiData = 0   (nao existe nenhuma em estoque)
    Toner Black  = 11  (nao mexer)

Uso:
    python corrigir_drums_5112.py
"""
import sys
sys.path.insert(0, '.')
from app import app, get_db

MODELO = 'ES5112/4172'
TIPO = 'Drum Black'


def registrar_mov(cur, estoque_id, antes, depois, motivo):
    if antes == depois:
        return
    cur.execute("""
        INSERT INTO estoque_movimentacoes
            (estoque_id, tipo_movimento, quantidade, saldo_antes, saldo_depois,
             motivo, responsavel, data_movimento)
        VALUES (%s, 'ajuste', %s, %s, %s, %s, 'sistema', CURRENT_TIMESTAMP)
    """, (estoque_id, depois - antes, antes, depois, motivo))


def main():
    with app.app_context():
        db = get_db()
        cur = db.cursor()
        try:
            cur.execute("""
                SELECT id, tipo_suprimento, nome_exibicao, marca, quantidade
                  FROM estoque
                 WHERE modelo_impressora = %s AND tipo_suprimento ILIKE '%%drum%%'
                 ORDER BY id
            """, (MODELO,))
            drums = cur.fetchall()
            print('Antes:')
            for d in drums:
                print(f"  id={d['id']} | {d['nome_exibicao'] or d['tipo_suprimento']} | marca={d['marca'] or '-'} | qtd={d['quantidade']}")

            if not drums:
                print('Nenhuma drum encontrada para este modelo. Nada a fazer.')
                return

            # A linha historica (menor id) passa a ser a R10 com 3 unidades,
            # pois a entrada real 'Voltou do concerto +3' pertence a ela.
            principal = drums[0]
            antes = int(principal['quantidade'] or 0)
            cur.execute("""
                UPDATE estoque
                   SET tipo_suprimento = %s,
                       marca = 'R10',
                       nome_exibicao = 'Drum R10',
                       quantidade = 3
                 WHERE id = %s
            """, (TIPO, principal['id']))
            registrar_mov(cur, principal['id'], antes, 3,
                          'Correcao: saldo real da Drum R10 (fusao indevida por marca)')

            # Remove eventuais outras linhas de drum duplicadas deste modelo
            for extra in drums[1:]:
                cur.execute("UPDATE estoque_movimentacoes SET estoque_id=%s WHERE estoque_id=%s",
                            (principal['id'], extra['id']))
                cur.execute("DELETE FROM estoque WHERE id=%s", (extra['id'],))
                print(f"  linha duplicada id={extra['id']} removida")

            # Garante a linha OKIData zerada, para entradas futuras
            cur.execute("""
                SELECT id FROM estoque
                 WHERE tipo_suprimento=%s AND modelo_impressora=%s AND COALESCE(marca,'')='OKIData'
            """, (TIPO, MODELO))
            if not cur.fetchone():
                cur.execute("""
                    INSERT INTO estoque (tipo_suprimento, modelo_impressora, marca, quantidade, estoque_minimo, nome_exibicao)
                    VALUES (%s, %s, 'OKIData', 0, 1, 'Drum OkiData')
                """, (TIPO, MODELO))
                print('  linha Drum OkiData criada com saldo 0')

            db.commit()

            print('\nDepois:')
            cur.execute("""
                SELECT id, tipo_suprimento, nome_exibicao, marca, quantidade
                  FROM estoque WHERE modelo_impressora=%s ORDER BY id
            """, (MODELO,))
            for r in cur.fetchall():
                print(f"  id={r['id']} | {r['nome_exibicao'] or r['tipo_suprimento']} | marca={r['marca'] or '-'} | qtd={r['quantidade']}")
            print('\nOK - correcao aplicada.')
        except Exception as e:
            db.rollback()
            print(f'ERRO, nada foi alterado: {e}')
            raise
        finally:
            cur.close()


if __name__ == '__main__':
    main()
