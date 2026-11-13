import ast
import hashlib
import json
import unicodedata
import unittest
import uuid
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


class ValidacaoChamadosEntregaTest(unittest.TestCase):
    def setUp(self):
        self.ns = carregar_funcoes('normalizar_busca', '_autenticar_helpdesk_para_entrega',
                                   '_validar_chamados_entrega', constantes=('HELPDESK_STATUS_ABERTOS',))
        self.ns['uuid'] = uuid
        self.unidade = '11111111-1111-4111-8111-111111111111'
        self.empresa = '22222222-2222-4222-8222-222222222222'
        self.usuario = '33333333-3333-4333-8333-333333333333'
        self.chamados = [self.chamado(1), self.chamado(2)]
        self.unidades = [{'id': self.unidade, 'nome': 'Clínica Central'}]
        self.locais = [{'id': 90, 'unidade_nome': 'Clinica Central', 'empresa_nome': 'Empresa A'}]
        self.ns['_helpdesk_request'] = self.requisicao

    def chamado(self, chamado_id):
        return {'id': chamado_id, 'protocolo': str(1000 + chamado_id), 'status': 'em_andamento',
                'unit_id': self.unidade, 'company_id': self.empresa,
                'units': {'nome': 'Clínica Central'}, 'companies': {'nome': 'Empresa A'}}

    def requisicao(self, caminho, **_kwargs):
        if caminho == '/auth/v1/user':
            return 200, {'id': self.usuario}
        if caminho.startswith('/rest/v1/users?'):
            return 200, [{'role': 'tecnico', 'ativo': True}]
        if caminho.startswith('/rest/v1/tickets?'):
            return 200, self.chamados
        if caminho.startswith('/rest/v1/units?'):
            return 200, self.unidades
        raise AssertionError('Requisição inesperada')

    def validar(self, unidade_id=90, role='tecnico'):
        return self.ns['_validar_chamados_entrega'](
            CursorFalso(self.locais), unidade_id, [1, 2], {'id': self.usuario, 'role': role})

    def test_autentica_usuario_ativo_com_permissao(self):
        usuario, erro, status = self.ns['_autenticar_helpdesk_para_entrega']('sessao-teste')
        self.assertEqual(usuario, {'id': self.usuario, 'role': 'tecnico'})
        self.assertIsNone(erro)
        self.assertEqual(status, 200)

    def test_valida_chamados_e_obtem_protocolos_do_servidor(self):
        selecionados, erro, status = self.validar()
        self.assertIsNone(erro)
        self.assertEqual(status, 200)
        self.assertEqual(selecionados, [
            {'chamado_id': 1, 'chamado_protocolo': '1001', 'unit_id': self.unidade, 'status': 'em_andamento'},
            {'chamado_id': 2, 'chamado_protocolo': '1002', 'unit_id': self.unidade, 'status': 'em_andamento'}])

    def test_rejeita_unidade_empresa_ou_chamado_incorretos(self):
        self.assertEqual(self.validar(unidade_id=91)[2], 409)
        self.locais[0]['empresa_nome'] = 'Outra empresa'
        self.assertEqual(self.validar()[2], 409)
        self.chamados[1]['unit_id'] = '44444444-4444-4444-8444-444444444444'
        self.assertEqual(self.validar()[2], 409)

    def test_rejeita_unidades_ambiguas_em_qualquer_banco(self):
        self.locais.append({'id': 91, 'unidade_nome': 'Clínica Central', 'empresa_nome': 'Empresa A'})
        self.assertEqual(self.validar()[2], 409)
        self.locais.pop()
        self.unidades.append({'id': '44444444-4444-4444-8444-444444444444', 'nome': 'Clinica Central'})
        self.assertEqual(self.validar()[2], 409)

    def test_rejeita_chamado_fechado_ou_tecnico_sem_transicao(self):
        self.chamados[1]['status'] = 'finalizado'
        self.assertEqual(self.validar()[2], 409)
        self.chamados[1]['status'] = 'aberto'
        self.assertEqual(self.validar()[2], 403)
        self.assertEqual(self.validar(role='admin')[2], 200)

    def test_falha_de_consulta_nao_libera_saida(self):
        self.ns['_helpdesk_request'] = lambda *_args, **_kwargs: (503, {})
        self.assertEqual(self.validar()[2], 503)
        self.assertEqual(self.ns['_autenticar_helpdesk_para_entrega']('sessao-teste')[2], 503)


class OperacaoEntregaMobileTest(unittest.TestCase):
    def setUp(self):
        ns = carregar_funcoes('_identificar_operacao_entrega')
        ns.update({'hashlib': hashlib, 'json': json})
        self.identificar = ns['_identificar_operacao_entrega']
        self.campos = {'unidade_id': 90, 'itens': [{'quantidade': 3}]}
        self.operacao = 'b0fd7677-b185-4217-a066-7ee784c7e787'

    def test_primeira_tentativa_bloqueia_operacao_e_nao_retorna_entrega(self):
        cursor = CursorFalso(None)
        dados_hash, anterior, erro = self.identificar(cursor, self.operacao, self.campos, 'Renan')
        self.assertEqual(len(dados_hash), 64)
        self.assertIsNone(anterior)
        self.assertIsNone(erro)
        self.assertIn('pg_advisory_xact_lock', cursor.consultas[0][0])

    def test_repeticao_retorna_mesma_entrega_e_rejeita_dados_ou_operador_diferentes(self):
        dados_hash, _, _ = self.identificar(CursorFalso(None), self.operacao, self.campos, 'Renan')
        anterior = {'dados_hash': dados_hash, 'operador': 'Renan', 'entrega_id': 7,
                    'entrega_existente': 7, 'unidade': 'Unidade A'}
        _, resultado, erro = self.identificar(CursorFalso(anterior), self.operacao, self.campos, 'Renan')
        self.assertEqual(resultado['entrega_id'], 7)
        self.assertIsNone(erro)
        _, resultado, erro = self.identificar(CursorFalso(anterior), self.operacao, self.campos, 'Kaio')
        self.assertIsNone(resultado)
        self.assertIn('outros dados', erro)
        _, resultado, erro = self.identificar(CursorFalso(anterior), self.operacao, {'unidade_id': 91}, 'Renan')
        self.assertIsNone(resultado)
        self.assertIn('outros dados', erro)

    def test_entrega_excluida_nao_pode_ser_recriada_por_repeticao(self):
        dados_hash, _, _ = self.identificar(CursorFalso(None), self.operacao, self.campos, 'Renan')
        anterior = {'dados_hash': dados_hash, 'operador': 'Renan', 'entrega_id': 7,
                    'entrega_existente': None, 'unidade': None}
        _, resultado, erro = self.identificar(CursorFalso(anterior), self.operacao, self.campos, 'Renan')
        self.assertIsNone(resultado)
        self.assertIn('excluída', erro)


class HistoricosEntregaRecuperaveisTest(unittest.TestCase):
    def setUp(self):
        self.ns = carregar_funcoes('_preparar_historicos_entrega', '_sincronizar_historicos_entrega')
        self.ns['uuid'] = uuid
        self.operacao = 'b0fd7677-b185-4217-a066-7ee784c7e787'

    def test_registra_apenas_chamados_selecionados_com_identificadores_estaveis(self):
        primeiro = CursorFalso()
        segundo = CursorFalso()
        self.ns['_preparar_historicos_entrega'](primeiro, self.operacao, [12, 24], 'Entrega #7')
        self.ns['_preparar_historicos_entrega'](segundo, self.operacao, [12, 24], 'Entrega #7')
        dados = [params for _, params in primeiro.consultas]
        self.assertEqual(dados, [params for _, params in segundo.consultas])
        self.assertEqual([item[1] for item in dados], [12, 24])
        self.assertNotEqual(dados[0][2], dados[1][2])

    def test_retomada_reutiliza_id_do_evento_apos_resposta_perdida(self):
        evento = {'chamado_id': 12, 'evento_id': uuid.uuid4(), 'descricao': 'Entrega #7'}
        cursor = CursorFalso([evento], [evento])

        class Banco:
            def cursor(self):
                return cursor
            def commit(self):
                pass

        eventos_remotos = set()
        tentativas = []
        def request(_caminho, **kwargs):
            evento_id = kwargs['payload']['id']
            eventos_remotos.add(evento_id)
            tentativas.append(evento_id)
            return (0 if len(tentativas) == 1 else 204), None

        self.ns['_helpdesk_request'] = request
        banco = Banco()
        self.assertEqual(self.ns['_sincronizar_historicos_entrega'](banco, self.operacao), [12])
        self.assertEqual(self.ns['_sincronizar_historicos_entrega'](banco, self.operacao), [])
        self.assertEqual(len(eventos_remotos), 1)
        self.assertEqual(tentativas[0], tentativas[1])

    def test_falha_de_comunicacao_mantem_evento_pendente_e_nao_impede_outros(self):
        eventos = [
            {'chamado_id': 12, 'evento_id': uuid.uuid4(), 'descricao': 'Entrega #7'},
            {'chamado_id': 24, 'evento_id': uuid.uuid4(), 'descricao': 'Entrega #7'},
        ]
        cursor = CursorFalso(eventos)

        class Banco:
            commits = 0
            def cursor(self):
                return cursor
            def commit(self):
                self.commits += 1

        chamadas = []
        def request(caminho, **kwargs):
            chamadas.append((caminho, kwargs))
            return (0 if len(chamadas) == 1 else 204), None

        self.ns['_helpdesk_request'] = request
        banco = Banco()
        falhas = self.ns['_sincronizar_historicos_entrega'](banco, self.operacao)
        self.assertEqual(falhas, [12])
        self.assertEqual(banco.commits, 2)
        self.assertEqual(cursor.consultas[-1][1], (self.operacao, 24))
        self.assertEqual(chamadas[0][1]['payload']['id'], str(eventos[0]['evento_id']))
        self.assertIn('ignore-duplicates', chamadas[0][1]['headers']['Prefer'])
        self.assertIn('on_conflict=id', chamadas[0][0])


class VinculoEntregaSelecionadaTest(unittest.TestCase):
    def setUp(self):
        self.vincular = carregar_funcoes('vincular_entrega_a_viagem')['vincular_entrega_a_viagem']
        self.entrega = {'id': 7, 'unidade_id': 90, 'viagem_id': None,
                        'parada_id': 55, 'chamado_id': 12, 'chamado_protocolo': 'A'}
        self.parada = {'viagem_id': 3, 'chamado_id': 24, 'chamado_protocolo': 'B'}
        self.chamados = [{'chamado_id': 12, 'chamado_protocolo': 'A'},
                         {'chamado_id': 24, 'chamado_protocolo': 'B'}]

    def cursor(self):
        return CursorFalso(self.entrega, self.parada, self.chamados,
                           {'total': 1, 'atendidas': 0})

    def test_selecao_vazia_nao_altera_a_viagem(self):
        cursor = self.cursor()
        with self.assertRaisesRegex(ValueError, 'Selecione pelo menos um chamado'):
            self.vincular(cursor, 7, chamados_selecionados=[])
        self.assertFalse(cursor.consultas)

    def test_selecao_invalida_ou_repetida_nao_altera_a_viagem(self):
        for selecionados in ([{'chamado_id': True}], [{'chamado_id': 1.5}],
                             [{'chamado_id': 0}], [{'chamado_id': 12}, {'chamado_id': '12'}]):
            with self.subTest(selecionados=selecionados):
                cursor = self.cursor()
                with self.assertRaises(ValueError):
                    self.vincular(cursor, 7, chamados_selecionados=selecionados)
                self.assertFalse(cursor.consultas)

    def test_ids_em_texto_sao_comparados_com_ids_numericos_da_parada(self):
        cursor = self.cursor()
        self.vincular(cursor, 7, chamados_selecionados=[
            {'chamado_id': '12'}, {'chamado_id': '24'}])
        self.assertTrue(any("UPDATE viagens_paradas SET status='atendida'" in sql
                            for sql, _ in cursor.consultas))

    def test_selecao_parcial_preserva_chamado_principal_e_parada_pendente(self):
        cursor = self.cursor()
        selecionados = [self.chamados[0], {'chamado_id': 33, 'chamado_protocolo': 'C'}]
        vinculo = self.vincular(cursor, 7, chamados_selecionados=selecionados)
        self.assertEqual(vinculo['chamados'], selecionados)
        self.assertEqual(vinculo['chamado_id'], 12)
        consultas = [sql for sql, _ in cursor.consultas]
        self.assertFalse(any("UPDATE viagens_paradas SET status='atendida'" in sql for sql in consultas))
        atualizacao = next(sql for sql in consultas if 'UPDATE suprimentos_entregas' in sql)
        self.assertNotIn('chamado_id=', atualizacao)

    def test_todos_chamados_da_parada_selecionados_permitem_marcar_atendida(self):
        cursor = self.cursor()
        self.vincular(cursor, 7, chamados_selecionados=self.chamados)
        self.assertTrue(any("UPDATE viagens_paradas SET status='atendida'" in sql
                            for sql, _ in cursor.consultas))

    def test_fluxo_antigo_conserva_comportamento_da_parada(self):
        cursor = self.cursor()
        vinculo = self.vincular(cursor, 7)
        self.assertEqual(vinculo['chamados'], self.chamados)
        self.assertEqual(vinculo['chamado_id'], 24)
        atualizacao = next(sql for sql, _ in cursor.consultas if 'UPDATE suprimentos_entregas' in sql)
        self.assertIn('chamado_id=', atualizacao)


class ValidacaoEstoqueEntregaTest(unittest.TestCase):
    def setUp(self):
        self.ns = carregar_funcoes(
            '_modelo_com_marca', '_remover_acentos', '_normalizar_tipo_suprimento',
            '_chave_estoque', '_chave_item_saida', 'verificar_saldo',
            '_verificar_faltantes_entrega')
        self.item = {'tipo_suprimento': 'Toner', 'modelo_impressora': 'M404',
                     'quantidade': 3}

    def test_soma_itens_repetidos_e_trava_saldo(self):
        cursor = CursorFalso({'quantidade': 5})
        faltantes, debitos = self.ns['_verificar_faltantes_entrega'](
            cursor, [self.item, self.item], bloquear=True)
        self.assertEqual(faltantes[0]['solicitado'], 6)
        self.assertEqual(debitos, [])
        self.assertIn('FOR UPDATE', cursor.consultas[0][0])

    def test_soma_itens_repetidos_em_um_unico_debito(self):
        cursor = CursorFalso({'quantidade': 6})
        faltantes, debitos = self.ns['_verificar_faltantes_entrega'](
            cursor, [self.item, self.item])
        self.assertFalse(faltantes)
        self.assertEqual(debitos, [('Toner', 'M404', None, 6)])


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

    def test_bloqueia_itens_repetidos_acima_da_carga(self):
        cursor = CursorFalso(self.parada, [self.carga(5)])
        item = {**self.item, 'quantidade': 3}
        _, _, alocacao, erros = self.validar(cursor, 55, 90, [item, item])
        self.assertIsNone(alocacao)
        self.assertIn('disponivel na carga: 2', erros[0])

    def test_trava_viagem_e_carga_na_confirmacao(self):
        cursor = CursorFalso(self.parada, {'status': 'em_rota'}, [self.carga(5)])
        parada, _, _, erros = self.validar(cursor, 55, 90, [self.item], bloquear=True)
        self.assertEqual(parada, 55)
        self.assertFalse(erros)
        self.assertIn('FOR UPDATE', cursor.consultas[1][0])
        self.assertIn('FOR UPDATE', cursor.consultas[2][0])

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
