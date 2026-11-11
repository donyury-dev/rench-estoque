import ast
import json
import unittest
from pathlib import Path

from werkzeug.datastructures import MultiDict


def carregar_coletor():
    caminho = Path(__file__).with_name('app.py')
    arvore = ast.parse(caminho.read_text(encoding='utf-8'))
    funcao = next(no for no in arvore.body if isinstance(no, ast.FunctionDef) and no.name == '_coletar_paradas_viagem')
    modulo = ast.Module(body=[funcao], type_ignores=[])
    namespace = {'json': json}
    exec(compile(ast.fix_missing_locations(modulo), str(caminho), 'exec'), namespace)
    return namespace['_coletar_paradas_viagem']


class ColetarParadasViagemTest(unittest.TestCase):
    def setUp(self):
        self.coletar = carregar_coletor()

    def test_preserva_unidades_e_chamados_validos(self):
        form = MultiDict([
            ('parada_unidade_id[]', '10'),
            ('parada_unidade_busca[]', 'Mercadão - Peruíbe — Mercadão'),
            ('parada_chamado_id[]', '603'),
            ('parada_chamado_protocolo[]', '2026000602'),
            ('parada_chamados_json[]', '[{"id": 603, "protocolo": "2026000602"}]'),
        ])
        self.assertEqual(self.coletar(form), [{
            'unidade_id': 10,
            'chamado_id': 603,
            'chamado_protocolo': '2026000602',
            'chamados': [(603, '2026000602')],
        }])

    def test_bloqueia_nome_digitado_sem_unidade_reconhecida(self):
        form = MultiDict([
            ('parada_unidade_id[]', ''),
            ('parada_unidade_busca[]', 'Nome com grafia diferente'),
            ('parada_chamado_id[]', ''),
            ('parada_chamado_protocolo[]', ''),
            ('parada_chamados_json[]', '[]'),
        ])
        with self.assertRaisesRegex(ValueError, 'não foi reconhecido'):
            self.coletar(form)

    def test_bloqueia_identificador_de_unidade_invalido(self):
        form = MultiDict([
            ('parada_unidade_id[]', 'texto-invalido'),
            ('parada_unidade_busca[]', 'Unidade'),
        ])
        with self.assertRaisesRegex(ValueError, 'inválida'):
            self.coletar(form)

    def test_ignora_somente_parada_completamente_vazia(self):
        form = MultiDict([
            ('parada_unidade_id[]', ''),
            ('parada_unidade_busca[]', ''),
            ('parada_chamado_id[]', ''),
            ('parada_chamado_protocolo[]', ''),
            ('parada_chamados_json[]', '[]'),
        ])
        self.assertEqual(self.coletar(form), [])


if __name__ == '__main__':
    unittest.main()
