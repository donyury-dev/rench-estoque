import unittest
from datetime import datetime

from equipamentos_duplicados import (
    buscar_serie_duplicada,
    combinar_registros,
    escolher_registro_principal,
    normalizar_numero_serie,
    unificar_series_duplicadas,
)


class CursorFalso:
    def __init__(self, resultado=None):
        self.resultado = resultado
        self.sql = None
        self.params = None

    def execute(self, sql, params):
        self.sql = sql
        self.params = params

    def fetchone(self):
        return self.resultado


class NumeroSerieTest(unittest.TestCase):
    def test_normaliza_maiusculas_espacos_e_bordas(self):
        self.assertEqual(normalizar_numero_serie('  ak5c034556  '), 'AK5C034556')
        self.assertEqual(normalizar_numero_serie('ab   12'), 'AB 12')

    def test_ignores_vazio_e_marcadores_sem_serie(self):
        for valor in (None, '', ' ', 'sn', 'S/N', 'sem serie', 'NUM SERIE'):
            self.assertIsNone(normalizar_numero_serie(valor), valor)

    def test_consulta_apenas_ativos_e_permite_editar_o_mesmo_registro(self):
        cursor = CursorFalso()
        self.assertIsNone(buscar_serie_duplicada(cursor, 'ab12', excluir_id=10))
        self.assertIn('ativo=1', cursor.sql)
        self.assertIn('id<>%s', cursor.sql)
        self.assertEqual(cursor.params, ['AB12', 10])

    def test_retorna_equipamento_que_ja_tem_a_serie(self):
        existente = {'id': 5, 'codigo': 'RCH-IMP-000005', 'modelo': 'C711'}
        cursor = CursorFalso(existente)
        self.assertEqual(buscar_serie_duplicada(cursor, 'ab12'), existente)


class UnificacaoTest(unittest.TestCase):
    def test_escolhe_registro_com_movimentacao_mais_recente(self):
        antigo = {'id': 1, 'ultima_movimentacao': datetime(2026, 10, 1)}
        recente = {'id': 2, 'ultima_movimentacao': datetime(2026, 11, 1)}
        self.assertEqual(escolher_registro_principal([antigo, recente]), recente)

    def test_em_empate_prefere_cadastro_mais_antigo(self):
        data = datetime(2026, 10, 9, 14, 18, 31)
        antigo = {'id': 1, 'ultima_movimentacao': data}
        novo = {'id': 2, 'ultima_movimentacao': data}
        self.assertEqual(escolher_registro_principal([novo, antigo]), antigo)

    def test_preserva_local_do_principal_e_completa_dados_e_observacoes(self):
        principal = {
            'id': 2,
            'codigo': 'RCH-IMP-000002',
            'local_atual_nome': 'R10 - SP',
            'modelo': None,
            'fabricante': 'OKI',
            'observacoes': 'Em manutenção',
            'contador_mono': 120,
            'contador_color': 20,
        }
        origem = {
            'id': 1,
            'codigo': 'RCH-IMP-000001',
            'local_atual_nome': 'Depósito',
            'modelo': 'C711',
            'fabricante': 'Oki Data',
            'observacoes': 'Não puxa papel',
            'contador_mono': 100,
            'contador_color': 30,
        }
        resultado = combinar_registros(principal, [origem])
        self.assertEqual(resultado['local_atual_nome'], 'R10 - SP')
        self.assertEqual(resultado['modelo'], 'C711')
        self.assertEqual(resultado['fabricante'], 'OKI')
        self.assertEqual(resultado['contador_mono'], 120)
        self.assertEqual(resultado['contador_color'], 30)
        self.assertIn('Em manutenção', resultado['observacoes'])
        self.assertIn('Não puxa papel', resultado['observacoes'])
    def test_unificacao_transfere_historicos_e_arquivia_copia(self):
        class CursorUnificacao:
            def __init__(self):
                self.chamadas = []
                self.consultas = 0

            def execute(self, sql, params=None):
                self.chamadas.append((' '.join(sql.split()), params))
                if 'SELECT e.*' in sql:
                    self.consultas += 1

            def fetchall(self):
                if self.consultas == 0:
                    return [{'serie': 'AK5C034556'}]
                return [
                    {'id': 1, 'codigo': 'RCH-IMP-000001', 'numero_serie': 'AK5C034556',
                     'ultima_movimentacao': datetime(2026, 10, 9), 'modelo': 'C711', 'tipo_equipamento': 'impressora',
                     'local_atual_nome': 'R10 - SP', 'observacoes': 'Observação antiga', 'ativo': 1},
                    {'id': 2, 'codigo': 'RCH-IMP-000002', 'numero_serie': 'AK5C034556',
                     'ultima_movimentacao': datetime(2026, 11, 10), 'modelo': 'C711', 'tipo_equipamento': 'impressora',
                     'local_atual_nome': 'R10 - SP', 'observacoes': 'Em reparo', 'ativo': 1},
                ]

        class BancoFalso:
            def __init__(self):
                self.cur = CursorUnificacao()
                self.committed = False

            def cursor(self):
                return self.cur

            def commit(self):
                self.committed = True

        banco = BancoFalso()
        resultado = unificar_series_duplicadas(banco)
        self.assertEqual(resultado, [{'serie': 'AK5C034556', 'mantido_id': 2, 'arquivados_ids': [1]}])
        comandos = [sql for sql, _ in banco.cur.chamadas]
        self.assertTrue(any('UPDATE movimentacoes SET equipamento_id=%s' in sql for sql in comandos))
        self.assertTrue(any('UPDATE historico_defeitos SET equipamento_id=%s' in sql for sql in comandos))
        self.assertTrue(any('SET ativo=0' in sql for sql in comandos))
        self.assertTrue(any('INSERT INTO equipamentos_unificacoes' in sql for sql in comandos))
        self.assertTrue(any('CREATE TRIGGER trg_equipamento_serie_unica' in sql for sql in comandos))
        self.assertTrue(banco.committed)
    def test_nao_unifica_cadastros_com_modelo_status_ou_tipo_divergente(self):
        from unittest.mock import MagicMock

        for diferenca in ({'modelo': 'M2170'}, {'status': 'inativo'}, {'tipo_equipamento': 'notebook'}):
            banco = MagicMock()
            cursor = banco.cursor.return_value
            registro = {
                'id': 1, 'numero_serie': 'SERIE1', 'tipo_equipamento': 'impressora',
                'modelo': 'M1120', 'local_atual_nome': 'Depósito', 'status': 'ativo',
            }
            cursor.fetchall.side_effect = [
                [{'serie': 'SERIE1'}],
                [registro, {**registro, 'id': 2, **diferenca}],
            ]
            self.assertEqual(unificar_series_duplicadas(banco), [])
            comandos = [chamada.args[0] for chamada in cursor.execute.call_args_list]
            self.assertFalse(any('INSERT INTO equipamentos_unificacoes' in sql for sql in comandos))
            self.assertFalse(any('UPDATE movimentacoes' in sql for sql in comandos))
            self.assertTrue(any('CREATE TRIGGER trg_equipamento_serie_unica' in sql for sql in comandos))

    def test_unifica_cadastros_com_marca_no_modelo_ou_local_divergente(self):
        from unittest.mock import MagicMock

        for diferenca in ({'modelo': 'EPSON M1120', 'local_atual_nome': 'Outra unidade'},):
            banco = MagicMock()
            cursor = banco.cursor.return_value
            registro = {
                'id': 1, 'numero_serie': 'SERIE1', 'tipo_equipamento': 'impressora',
                'modelo': 'M1120', 'local_atual_nome': 'Depósito', 'status': 'ativo',
                'ultima_movimentacao': datetime(2026, 11, 1),
            }
            segundo = {**registro, 'id': 2, 'ultima_movimentacao': datetime(2026, 10, 1), **diferenca}
            cursor.fetchall.side_effect = [
                [{'serie': 'SERIE1'}],
                [registro, segundo],
            ]
            self.assertEqual(
                unificar_series_duplicadas(banco),
                [{'serie': 'SERIE1', 'mantido_id': 1, 'arquivados_ids': [2]}],
            )
            comandos = [chamada.args[0] for chamada in cursor.execute.call_args_list]
            self.assertTrue(any('INSERT INTO equipamentos_unificacoes' in sql for sql in comandos))
            self.assertTrue(any('UPDATE movimentacoes SET equipamento_id=%s' in sql for sql in comandos))


if __name__ == '__main__':
    unittest.main()
