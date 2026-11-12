import ast
import unicodedata
import unittest
from pathlib import Path

from werkzeug.datastructures import MultiDict


APP_PATH = Path(__file__).resolve().with_name('app.py')


def carregar_funcoes(*nomes, constantes=()):
    """Executa somente as funções necessárias, sem inicializar Flask ou banco."""
    arvore = ast.parse(APP_PATH.read_text(encoding='utf-8'))
    selecionados = []
    for no in arvore.body:
        if isinstance(no, (ast.FunctionDef, ast.AsyncFunctionDef)) and no.name in nomes:
            no.decorator_list = []
            selecionados.append(no)
        elif isinstance(no, ast.Assign) and any(
                isinstance(alvo, ast.Name) and alvo.id in constantes for alvo in no.targets):
            selecionados.append(no)
    encontrados = {no.name for no in selecionados if isinstance(no, ast.FunctionDef)}
    if encontrados != set(nomes):
        raise AssertionError(f'Funções não encontradas: {set(nomes) - encontrados}')
    modulo = ast.fix_missing_locations(ast.Module(body=selecionados, type_ignores=[]))
    namespace = {'unicodedata': unicodedata}
    exec(compile(modulo, str(APP_PATH), 'exec'), namespace)
    return namespace


class CursorFalso:
    def __init__(self, *respostas):
        self.respostas = list(respostas)
        self.consultas = []

    def execute(self, sql, params=None):
        self.consultas.append((sql, params))

    def _proxima(self):
        if not self.respostas:
            raise AssertionError('Consulta inesperada no cursor mockado')
        return self.respostas.pop(0)

    def fetchall(self):
        return self._proxima()

    def fetchone(self):
        return self._proxima()


class AuditoriaConsultaTest(unittest.TestCase):
    def setUp(self):
        self.ns = carregar_funcoes(
            '_consultar_auditoria', constantes=('_EVENTOS_AUDITORIA_SQL',))
        self.consultar = self.ns['_consultar_auditoria']

    def test_une_historicos_e_parametrizar_periodo_texto_e_categoria(self):
        cursor = CursorFalso({'total': 26}, [{'evento_id': '26'}])
        resultado = self.consultar(
            cursor, data_inicio='2025-01-01', data_fim='2025-01-31',
            busca='Kaio toner', categoria='viagem', pagina=2, por_pagina=25)

        self.assertEqual(resultado['total'], 26)
        self.assertEqual(resultado['pagina'], 2)
        self.assertEqual(resultado['total_paginas'], 2)
        self.assertEqual(resultado['inicio'], 26)
        self.assertEqual(resultado['fim'], 26)
        sql_contagem, params_contagem = cursor.consultas[0]
        self.assertIn('FROM estoque_movimentacoes em', sql_contagem)
        self.assertIn('FROM movimentacoes m', sql_contagem)
        self.assertIn('FROM viagens_coletas vc', sql_contagem)
        self.assertIn('FROM suprimentos_entregas se', sql_contagem)
        self.assertIn('categoria = %s', sql_contagem)
        self.assertIn('data_evento >= %s::date', sql_contagem)
        self.assertIn("data_evento < %s::date + INTERVAL '1 day'", sql_contagem)
        self.assertIn('ILIKE %s', sql_contagem)
        self.assertNotIn('Kaio toner', sql_contagem)
        self.assertEqual(params_contagem, [
            'viagem', '2025-01-01', '2025-01-31', '%Kaio toner%'])
        _, params_eventos = cursor.consultas[1]
        self.assertEqual(params_eventos[-2:], [25, 25])

    def test_tipo_de_estoque_e_paginacao_sao_limitados(self):
        cursor = CursorFalso({'total': 0}, [])
        resultado = self.consultar(
            cursor, categoria='estoque', tipo_movimento='saida',
            pagina=999, por_pagina=9999)

        self.assertEqual(resultado['pagina'], 1)
        self.assertEqual(resultado['total_paginas'], 1)
        self.assertEqual(resultado['por_pagina'], 200)
        self.assertEqual(resultado['inicio'], 0)
        self.assertEqual(resultado['fim'], 0)
        sql, params = cursor.consultas[1]
        self.assertIn("(categoria = 'estoque' AND acao = %s)", sql)
        self.assertIn('LIMIT %s OFFSET %s', sql)
        self.assertEqual(params, ['estoque', 'saida', 200, 0])

    def test_exportacao_respeita_filtro_e_teto_de_linhas(self):
        cursor = CursorFalso({'total': 5001}, [{'evento_id': '1'}])
        resultado = self.consultar(
            cursor, busca='cabos', pagina=8, por_pagina=25, exportar=True)

        self.assertEqual(resultado['pagina'], 1)
        self.assertEqual(resultado['inicio'], 1)
        self.assertEqual(resultado['fim'], 1)
        self.assertTrue(resultado['exportacao_truncada'])
        self.assertEqual(resultado['limite_exportacao'], 5000)
        self.assertEqual(cursor.consultas[0][1], ['%cabos%'])
        self.assertEqual(cursor.consultas[1][1], ['%cabos%', 5000, 0])


class EstoquePorLocalTest(unittest.TestCase):
    def setUp(self):
        self.ns = carregar_funcoes(
            'normalizar_busca', 'preparar_termos_busca', 'texto_combinado',
            '_consultar_itens_estoque_viagem', '_consultar_estoque_por_local',
            '_reservados_estoque', constantes=('_STATUS_VIAGENS_ATIVAS',))
        self.itens = [
            {'id': 1, 'tipo_suprimento': 'Toner', 'modelo_impressora': 'M404',
             'marca': 'ES', 'nome_exibicao': 'Toner preto', 'quantidade': 8,
             'estoque_minimo': 2},
            {'id': 2, 'tipo_suprimento': 'Cilindro', 'modelo_impressora': 'M404',
             'marca': 'ES', 'nome_exibicao': None, 'quantidade': 4,
             'estoque_minimo': 1},
        ]
        self.cargas = [
            self.carga(viagem_id=10, numero='VJ-000010', status='em_rota',
                       tecnico='João', carregada=10, entregue=3, usada=1,
                       devolvida=2, rota='Unidade A'),
            self.carga(viagem_id=11, numero='VJ-000011', status='finalizada',
                       tecnico='Maria', carregada=5, entregue=5, usada=0,
                       devolvida=0, rota='Cliente B'),
        ]

    @staticmethod
    def carga(viagem_id, numero, status, tecnico, carregada, entregue, usada,
              devolvida, rota):
        return {
            'estoque_id': 1, 'tipo_suprimento': 'Toner',
            'modelo_impressora': 'M404', 'marca': 'ES',
            'nome_exibicao': 'Toner preto', 'estoque_minimo': 2, 'deposito': 8,
            'viagem_id': viagem_id, 'viagem_numero': numero,
            'status_viagem': status, 'responsavel_atendimento': tecnico,
            'data_criacao': None, 'viagem_item_id': viagem_id * 10,
            'origem': 'estoque', 'fornecedor': None,
            'quantidade_carregada': carregada, 'quantidade_entregue': entregue,
            'quantidade_usada_manual': usada, 'quantidade_devolvida': devolvida,
            'unidades_rota': rota,
        }

    def consultar(self, cargas=None, **filtros):
        cursor = CursorFalso(self.itens, self.cargas if cargas is None else cargas)
        return self.ns['_consultar_estoque_por_local'](cursor, **filtros), cursor

    def test_resumo_nao_duplica_deposito_e_separa_carga_ativa_do_historico(self):
        resultado, cursor = self.consultar()

        self.assertEqual(len(resultado['posicoes']), 3)
        self.assertEqual(resultado['resumo'], {
            'deposito': 12, 'com_tecnico': 4, 'entregue': 8, 'devolvido': 2})
        self.assertEqual(resultado['posicoes'][0]['com_tecnico'], 4)
        self.assertEqual(resultado['posicoes'][1]['com_tecnico'], 0)
        self.assertIsNone(resultado['posicoes'][2]['viagem_id'])
        self.assertEqual(resultado['tecnicos'], ['João', 'Maria'])
        self.assertTrue(all('SELECT' in sql for sql, _ in cursor.consultas))

    def test_filtra_tecnico_sem_diferenciar_acentos_e_status(self):
        resultado, _ = self.consultar(tecnico='joao', status_viagem='em_rota')
        self.assertEqual(len(resultado['posicoes']), 1)
        self.assertEqual(resultado['posicoes'][0]['viagem_numero'], 'VJ-000010')
        self.assertEqual(resultado['resumo']['entregue'], 3)

        resultado, _ = self.consultar(tecnico='João', status_viagem='finalizada')
        self.assertEqual(resultado['posicoes'], [])

    def test_busca_combina_item_viagem_e_rota_e_aplica_limite(self):
        resultado, _ = self.consultar(busca='toner cliente VJ-000011')
        self.assertEqual(len(resultado['posicoes']), 1)
        self.assertEqual(resultado['posicoes'][0]['responsavel_atendimento'], 'Maria')

        resultado, _ = self.consultar(limite=1)
        self.assertEqual(resultado['total'], 3)
        self.assertEqual(len(resultado['posicoes']), 1)

    def test_reservados_reutiliza_consulta_e_somente_viagens_ativas(self):
        cargas = [
            self.carga(10, 'VJ-10', 'em_rota', 'A', 10, 2, 1, 1, ''),
            self.carga(11, 'VJ-11', 'aguardando_retorno', 'A', 4, 1, 0, 1, ''),
            self.carga(12, 'VJ-12', 'finalizada', 'A', 7, 0, 0, 0, ''),
        ]
        cursor = CursorFalso(cargas)
        reservados = self.ns['_reservados_estoque'](cursor)

        self.assertEqual(reservados, {1: 8})
        self.assertEqual(len(cursor.consultas), 1)
        sql, params = cursor.consultas[0]
        self.assertIn('WHERE v.status = ANY(%s)', sql)
        self.assertEqual(params, [list(self.ns['_STATUS_VIAGENS_ATIVAS'])])


class ValidacaoSaidaViagemTest(unittest.TestCase):
    def setUp(self):
        self.ns = carregar_funcoes(
            '_modelo_com_marca', '_remover_acentos', '_normalizar_tipo_suprimento',
            '_chave_estoque', '_chave_item_saida', 'validar_saida_contra_viagem',
            '_coletar_itens_entrega')
        self.validar = self.ns['validar_saida_contra_viagem']
        self.parada = {
            'id': 55, 'viagem_id': 7, 'unidade_id': 90,
            'status': 'em_rota', 'numero': 'VJ-000007',
        }
        self.item = {
            'tipo_suprimento': 'Toner', 'modelo_impressora': 'M404',
            'marca': None, 'cor_selecionada': None, 'quantidade': 1,
        }

    @staticmethod
    def carga(carregada, entregue=0, usada=0, origem='rench'):
        return {
            'tipo_suprimento': 'Toner', 'modelo_impressora': 'M404',
            'marca': None, 'origem': origem, 'pode_usar_cliente': True,
            'quantidade_carregada': carregada, 'quantidade_entregue': entregue,
            'quantidade_usada_manual': usada,
        }

    def test_bloqueia_parada_inexistente_sem_consultar_ou_alterar_carga(self):
        cursor = CursorFalso(None)
        parada, viagem, alocacao, erros = self.validar(cursor, 999, 90, [self.item])

        self.assertIsNone(parada)
        self.assertIsNone(viagem)
        self.assertIsNone(alocacao)
        self.assertIn('não existe', erros[0])
        self.assertEqual(len(cursor.consultas), 1)
        self.assertTrue(cursor.consultas[0][0].lstrip().startswith('SELECT'))

    def test_bloqueia_parada_de_outra_unidade(self):
        cursor = CursorFalso(self.parada)
        parada, viagem, alocacao, erros = self.validar(cursor, 55, 91, [self.item])

        self.assertIsNone(parada)
        self.assertIsNone(viagem)
        self.assertIsNone(alocacao)
        self.assertIn('não pertence à unidade', erros[0])
        self.assertEqual(len(cursor.consultas), 1)

    def test_bloqueia_quantidade_acima_do_disponivel_real_na_viagem(self):
        cursor = CursorFalso(self.parada, [self.carga(5, entregue=2, usada=1)])
        item = {**self.item, 'quantidade': 3}
        parada, viagem, alocacao, erros = self.validar(cursor, 55, 90, [item])

        self.assertIsNone(parada)
        self.assertIsNone(viagem)
        self.assertIsNone(alocacao)
        self.assertIn('disponivel na carga: 2', erros[0])
        self.assertEqual(len(cursor.consultas), 2)
        self.assertTrue(all(sql.lstrip().startswith('SELECT') for sql, _ in cursor.consultas))

    def test_permite_consumo_da_carga_e_separa_origem_fornecedor(self):
        cursor = CursorFalso(self.parada, [
            self.carga(4, entregue=2),
            self.carga(3, origem='fornecedor'),
        ])
        item = {**self.item, 'quantidade': 4}
        parada, viagem, alocacao, erros = self.validar(cursor, 55, '90', [item])

        self.assertEqual((parada, viagem, erros), (55, 7, []))
        self.assertEqual(alocacao[0]['rench'], 2)
        self.assertEqual(alocacao[0]['fornecedor'], 2)

    def test_quantidades_zero_e_negativas_nao_entram_na_entrega(self):
        form = MultiDict([
            ('tipo_suprimento[]', 'Toner'), ('quantidade[]', '0'),
            ('modelo_impressora[]', 'M404'),
            ('tipo_suprimento[]', 'Toner'), ('quantidade[]', '-2'),
            ('modelo_impressora[]', 'M404'),
        ])
        self.assertEqual(self.ns['_coletar_itens_entrega'](form), [])


if __name__ == '__main__':
    unittest.main()
