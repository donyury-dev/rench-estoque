import hashlib
import json
import unittest
import uuid
from datetime import date
from types import SimpleNamespace
from urllib.parse import urlparse

from rench_web.auditoria_estoque_test import CursorFalso, carregar_funcoes


class EntregaConjuntaTest(unittest.TestCase):
    def setUp(self):
        self.ns = carregar_funcoes('_parse_entrega_mobile', '_parse_fechamento_entrega', '_identificar_operacao_entrega')
        self.ns.update({'g': SimpleNamespace(operador_mobile='Tecnico'), 'date': date,
                        'uuid': uuid, 'json': json, 'hashlib': hashlib, 'urlparse': urlparse,
                        'HELPDESK_SUPABASE_URL': 'https://helpdesk.example'})
        self.dados = {
            'unidade_id': 1, 'observacoes': 'Entrega', 'chamado_id': 12,
            'chamado_protocolo': 'A', 'chamados_ids': [12, 24],
            'itens': [{'tipo_suprimento': 'Papel', 'quantidade': 3, 'motivo': 'Reposição'}],
        }
        self.fechamento = {
            'unit_id': str(uuid.uuid4()), 'signer_name': 'Cliente', 'solution': 'Serviço concluído',
            'signature_url': 'https://helpdesk.example/storage/v1/object/public/ticket-attachments/signatures/a.png',
        }

    def test_selecao_unica_e_motivo_preservado(self):
        erro, campos = self.ns['_parse_entrega_mobile'](self.dados)
        self.assertIsNone(erro)
        self.assertEqual(campos['chamados_ids'], [12, 24])
        self.assertEqual(campos['itens'][0]['outro'], 'Reposição')
        for ids in ([12, 12], [12, True], [12, 0], [12, 1.5], [24, 33]):
            with self.subTest(ids=ids):
                erro, _ = self.ns['_parse_entrega_mobile']({**self.dados, 'chamados_ids': ids})
                self.assertIsNotNone(erro)

    def test_assinatura_de_outro_dominio_ou_nome_invalido_e_rejeitado(self):
        self.assertIsNotNone(self.ns['_parse_fechamento_entrega'](self.fechamento))
        for chave, valor in [('signature_url', 'https://evil.example/storage/v1/object/public/ticket-attachments/signatures/a.png'),
                             ('signer_name', 'Cliente\nOutro'), ('solution', '')]:
            with self.subTest(chave=chave):
                self.assertIsNone(self.ns['_parse_fechamento_entrega']({**self.fechamento, chave: valor}))

    def test_repeticao_exige_mesmos_dados_e_operador(self):
        operacao = str(uuid.uuid4())
        campos = {'itens': [{'quantidade': 3}], 'unidade_id': 1}
        hash_esperado = hashlib.sha256(json.dumps(campos, sort_keys=True, ensure_ascii=False,
                                                 separators=(',', ':')).encode('utf-8')).hexdigest()
        anterior = {'dados_hash': hash_esperado, 'operador': 'Tecnico', 'entrega_id': 2,
                    'entrega_existente': 2, 'unidade': 'Unidade'}
        cursor = CursorFalso(anterior)
        _, encontrada, erro = self.ns['_identificar_operacao_entrega'](cursor, operacao, campos, 'Tecnico')
        self.assertIsNone(erro)
        self.assertEqual(encontrada['entrega_id'], 2)
        self.assertIn('pg_advisory_xact_lock', cursor.consultas[0][0])
        for novos_campos, operador in [({'unidade_id': 2}, 'Tecnico'), (campos, 'Outro')]:
            with self.subTest(operador=operador):
                _, encontrada, erro = self.ns['_identificar_operacao_entrega'](
                    CursorFalso(anterior), operacao, novos_campos, operador)
                self.assertIsNone(encontrada)
                self.assertIsNotNone(erro)

    def test_saida_sem_viagem_nao_e_vinculada_automaticamente_depois_da_confirmacao(self):
        vincular = carregar_funcoes('vincular_entrega_a_viagem')['vincular_entrega_a_viagem']
        entrega = {'id': 7, 'unidade_id': 90, 'viagem_id': None, 'parada_id': None,
                   'chamado_id': 12, 'chamado_protocolo': 'A'}
        cursor = CursorFalso(entrega)
        self.assertIsNone(vincular(cursor, 7, chamados_selecionados=[{'chamado_id': 12}, {'chamado_id': 24}]))
        self.assertEqual(len(cursor.consultas), 1)


if __name__ == '__main__':
    unittest.main()
