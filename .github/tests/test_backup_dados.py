import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

MODULE_PATH = Path(__file__).resolve().parents[1] / 'scripts' / 'backup_dados.py'
spec = importlib.util.spec_from_file_location('backup_dados', MODULE_PATH)
backup = importlib.util.module_from_spec(spec)
spec.loader.exec_module(backup)


class BackupDadosTest(unittest.TestCase):
    def test_aceita_somente_storage_publico_do_projeto(self):
        ref = 'projeto'
        url = f'https://{ref}.supabase.co/storage/v1/object/public/anexos/foto.jpg'
        entrada = backup.attachment_entry(url, ref)
        self.assertEqual(entrada['bucket'], 'anexos')
        self.assertEqual(entrada['object_path'], 'foto.jpg')
        self.assertIsNone(backup.attachment_entry('https://outro.supabase.co/storage/v1/object/public/anexos/foto.jpg', ref))
        inseguro = backup.attachment_entry('http://projeto.supabase.co/storage/v1/object/public/anexos/foto.jpg', ref)
        self.assertEqual(inseguro['status'], 'ignorado')
        self.assertEqual(inseguro['reason'], 'somente_https')
        privado = backup.attachment_entry(f'https://{ref}.supabase.co/storage/v1/object/sign/anexos/foto.jpg', ref)
        self.assertEqual(privado['status'], 'ignorado')
        self.assertEqual(privado['reason'], 'storage_privado_ou_url_assinada')

    def test_referencias_duplicadas_preservam_todas_as_origens(self):
        encontrados = {}
        url = 'https://projeto.supabase.co/storage/v1/object/public/anexos/foto.jpg'
        backup.collect_attachments({'url': url}, 'tickets', 1, '$', 'projeto', encontrados)
        backup.collect_attachments([url], 'events', 2, '$', 'projeto', encontrados)
        self.assertEqual(len(encontrados), 1)
        self.assertEqual(len(encontrados[url]['references']), 2)

    def test_inventario_e_checksums_detectam_alteracao(self):
        with tempfile.TemporaryDirectory() as tmp:
            outdir = Path(tmp)
            (outdir / 'backup.dump').write_bytes(b'dump')
            (outdir / 'tabela.json').write_text('[{"id": 1}]', encoding='utf-8')
            backup.write_json(outdir / backup.ATTACHMENTS_NAME, {'summary': {}, 'attachments': []})
            backup.write_inventory(outdir, 'projeto', 'backup.dump', [{'name': 'tabela', 'file': 'tabela.json', 'rows': 1}], {})
            with patch.object(backup.subprocess, 'run'):
                backup.validate_backup(outdir)
            (outdir / 'tabela.json').write_text('[{"id": 2}]', encoding='utf-8')
            with patch.object(backup.subprocess, 'run'):
                with self.assertRaisesRegex(ValueError, 'divergente'):
                    backup.validate_backup(outdir)

    def test_bloqueia_caminho_de_arquivo_inseguro(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(ValueError, 'inseguro'):
                backup.resolve_backup_file(Path(tmp), '../segredo')

    def test_anexo_privado_usa_credencial_sem_gravar_no_manifesto(self):
        with tempfile.TemporaryDirectory() as tmp:
            entry = backup.attachment_entry('https://projeto.supabase.co/storage/v1/object/sign/anexos/foto.jpg', 'projeto')
            response = MagicMock()
            response.__enter__.return_value = response
            response.geturl.return_value = 'https://projeto.supabase.co/storage/v1/object/anexos/foto.jpg'
            response.headers.get.return_value = '3'
            response.read.side_effect = [b'abc', b'']
            with patch.dict(backup.os.environ, {'SUPABASE_SERVICE_ROLE_KEY': 'segredo'}), patch.object(backup.urllib.request, 'urlopen', return_value=response) as abrir:
                backup.download_attachment(entry, Path(tmp), 100)
            self.assertEqual(entry['status'], 'baixado')
            request = abrir.call_args.args[0]
            self.assertIn('/object/anexos/foto.jpg', request.full_url)
            self.assertEqual(request.get_header('Authorization'), 'Bearer segredo')
            self.assertNotIn('segredo', json.dumps(entry))

    def test_restauracao_somente_no_banco_temporario_local(self):
        for url in ('postgresql://localhost/outro', 'postgresql://example.com/restore_test'):
            with self.subTest(url=url), patch.dict(backup.os.environ, {'RESTORE_DB_URL': url}):
                with self.assertRaises(ValueError):
                    backup.checked_restore_url()
        with patch.dict(backup.os.environ, {'RESTORE_DB_URL': 'postgresql://localhost/restore_test'}):
            self.assertEqual(backup.checked_restore_url(), 'postgresql://localhost/restore_test')


if __name__ == '__main__':
    unittest.main()
