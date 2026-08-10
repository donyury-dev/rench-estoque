# -*- coding: utf-8 -*-
"""Corrige o saldo das Drums ES5112/4172 apos o bug de saldo fantasma.

Estado errado encontrado:
  id=291 | Drum Black  | ES5112/4172 | OKIData | 8   (saldo fantasma)
  id=527 | Drum Teste automatizado | ES5112/4172 | R10 | 5   (nome corrompido)

Estado correto informado pelo responsavel:
  Drum R10     = 3
  Drum OkiData = 0
  Toner Black  = 11 (nao mexer)

Uso:
    python corrigir_drums_5112.py
"""
import sys
sys.path.insert(0, '.')
from app import app, get_db


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
            # --- 1. Restaura o item 527 (era a Drum Black R10 real) ---
            cur.execute("SELECT id, tipo_suprimento, quantidade FROM estoque WHERE id = 527")
            item = cur.fetchone()
            if item:
                antes = int(item['quantidade'] or 0)
                print(f"[527] antes: {item['tipo_suprimento']} qtd={antes}")
                cur.execute("""
                    UPDATE estoque
                       SET tipo_suprimento = 'Drum Black',
                           modelo_impressora = 'ES5112/4172',
                           marca = 'R10',
                           nome_exibicao = 'Drum R10',
                           quantidade = 3
                     WHERE id = 527
                """)
                registrar_mov(cur, 527, antes, 3,
                              'Correcao: restaurado nome Drum Black R10 e saldo real (3)')
                # desfaz a renomeacao que vazou para o historico de entregas
                cur.execute("""
                    UPDATE suprimentos_itens
                       SET tipo_suprimento = 'Drum Black'
                     WHERE tipo_suprimento ILIKE 'Drum Teste%'
                """)
                print(f"[527] depois: Drum Black / R10 / exib='Drum R10' / qtd=3")
                print(f"[527] itens de entrega corrigidos: {cur.rowcount}")
            else:
                print('[527] nao encontrado')

            # --- 2. Zera o saldo fantasma do OKIData (id 291) ---
            cur.execute("SELECT id, tipo_suprimento, quantidade FROM estoque WHERE id = 291")
            item = cur.fetchone()
            if item:
                antes = int(item['quantidade'] or 0)
                print(f"[291] antes: {item['tipo_suprimento']} qtd={antes}")
                cur.execute("""
                    UPDATE estoque
                       SET nome_exibicao = 'Drum OkiData',
                           quantidade = 0
                     WHERE id = 291
                """)
                registrar_mov(cur, 291, antes, 0,
                              'Correcao: remocao de saldo fantasma gerado pela migracao de marca')
                print("[291] depois: Drum Black / OKIData / exib='Drum OkiData' / qtd=0")
            else:
                print('[291] nao encontrado')

            db.commit()

            # --- 3. Confere resultado ---
            print('\n=== ESTADO FINAL ES5112/4172 ===')
            cur.execute("""
                SELECT id, tipo_suprimento, nome_exibicao, marca, quantidade
                  FROM estoque WHERE modelo_impressora = 'ES5112/4172' ORDER BY id
            """)
            for r in cur.fetchall():
                nome = r['nome_exibicao'] or r['tipo_suprimento']
                print(f"  id={r['id']} | {nome} | marca={r['marca'] or '-'} | qtd={r['quantidade']}")
            print('\nOK - correcao aplicada.')
        except Exception as e:
            db.rollback()
            print(f'ERRO, nada foi alterado: {e}')
            raise
        finally:
            cur.close()


if __name__ == '__main__':
    main()
