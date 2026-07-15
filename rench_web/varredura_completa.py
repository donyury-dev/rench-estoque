import sqlite3, json, csv, os
from datetime import datetime

DB_PATH = 'rench_web.db'
EXPORT_DIR = 'carregamentos_seguros'
os.makedirs(EXPORT_DIR, exist_ok=True)

ts = datetime.now().strftime('%Y%m%d_%H%M%S')
conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row
cur = conn.cursor()

def dump(table, columns, name):
    cur.execute(f"SELECT {','.join(columns)} FROM {table}")
    rows = [dict(r) for r in cur.fetchall()]
    with open(os.path.join(EXPORT_DIR, f'{name}_{ts}.json'), 'w', encoding='utf-8') as f:
        json.dump(rows, f, ensure_ascii=False, indent=2, default=str)
    if rows:
        with open(os.path.join(EXPORT_DIR, f'{name}_{ts}.csv'), 'w', encoding='utf-8-sig', newline='') as f:
            w = csv.DictWriter(f, fieldnames=columns)
            w.writeheader(); w.writerows(rows)
    print(f'{name}: {len(rows)}')
    return rows

# Dump completo de tudo
empresas = dump('empresas', ['id','nome','tipo','ativo'], 'empresas_full')
unidades = dump('unidades', ['id','empresa_id','nome','setor','ativo'], 'unidades_full')
equipamentos = dump('equipamentos', ['id','codigo','tipo_equipamento','fabricante','modelo','numero_serie','patrimonio','status','unidade_id','local_atual_nome','cliente_atual','observacoes','contador_mono','contador_color','data_cadastro','ativo'], 'equipamentos_full')
movimentacoes = dump('movimentacoes', ['id','equipamento_id','data_movimentacao','origem_local','origem_unidade','destino_local','destino_unidade','tipo_movimento','responsavel','observacoes','contador_mono_anterior','contador_mono_novo','contador_color_anterior','contador_color_novo'], 'movimentacoes_full')
defeitos = dump('historico_defeitos', ['id','equipamento_id','descricao','data_ocorrencia'], 'historico_defeitos_full')

conn.close()
print('FULL EXPORT OK')
