# -*- coding: utf-8 -*-
"""
carregar_seguro.py
==================
Roda ANTES de cada atualizacao do banco (git push para o Render).
Detecta registros criados no site de producao (empresas, unidades, equipamentos,
movimentacoes, historico_defeitos) e exporta para JSON/CSV.
Se no deploy as alteracoes forem perdidas, voce pode usar os arquivos gerados
para reimportar os dados novos sem perder nada.

Uso: python carregar_seguro.py
"""
import sqlite3, json, csv, os
from datetime import datetime

DB_PATH = 'rench_web.db'
EXPORT_DIR = 'carregamentos_seguros'
os.makedirs(EXPORT_DIR, exist_ok=True)

def load_ids(path, column='id'):
    if not os.path.exists(path):
        return set()
    with open(path, 'r', encoding='utf-8') as f:
        return {int(line.strip()) for line in f if line.strip().isdigit()}

def save_ids(path, ids):
    with open(path, 'w', encoding='utf-8') as f:
        for i in sorted(ids):
            f.write(f"{i}\n")

def dump_table(cur, table, columns, export_name, id_column='id'):
    cur.execute(f"SELECT {','.join(columns)} FROM {table}")
    rows = [dict(zip(columns, r)) for r in cur.fetchall()]
    # JSON
    json_path = os.path.join(EXPORT_DIR, f"{export_name}.json")
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(rows, f, ensure_ascii=False, indent=2, default=str)
    # CSV
    csv_path = os.path.join(EXPORT_DIR, f"{export_name}.csv")
    if rows:
        with open(csv_path, 'w', encoding='utf-8-sig', newline='') as f:
            w = csv.DictWriter(f, fieldnames=columns)
            w.writeheader()
            w.writerows(rows)
    return rows

def main():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    report = []

    # Snapshot de IDs atuais
    snapshot_files = {
        'empresas':'empresas_ids.txt',
        'unidades':'unidades_ids.txt',
        'equipamentos':'equipamentos_ids.txt',
        'movimentacoes':'movimentacoes_ids.txt',
        'historico_defeitos':'historico_defeitos_ids.txt',
    }
    snapshots = {k: load_ids(os.path.join(EXPORT_DIR, v)) for k, v in snapshot_files.items()}

    # Empresas
    emp_cols = ['id','nome','tipo','ativo']
    empresas = dump_table(cur, 'empresas', emp_cols, f'empresas_{ts}')
    novas_empresas = [r for r in empresas if r['id'] not in snapshots['empresas']]
    if novas_empresas:
        with open(os.path.join(EXPORT_DIR, f'empresas_novas_{ts}.json'), 'w', encoding='utf-8') as f:
            json.dump(novas_empresas, f, ensure_ascii=False, indent=2)
    save_ids(os.path.join(EXPORT_DIR, snapshot_files['empresas']), {r['id'] for r in empresas})
    report.append(f"Empresas: {len(empresas)} total, {len(novas_empresas)} novas")

    # Unidades
    uni_cols = ['id','empresa_id','nome','setor','ativo']
    unidades = dump_table(cur, 'unidades', uni_cols, f'unidades_{ts}')
    novas_unidades = [r for r in unidades if r['id'] not in snapshots['unidades']]
    if novas_unidades:
        with open(os.path.join(EXPORT_DIR, f'unidades_novas_{ts}.json'), 'w', encoding='utf-8') as f:
            json.dump(novas_unidades, f, ensure_ascii=False, indent=2)
    save_ids(os.path.join(EXPORT_DIR, snapshot_files['unidades']), {r['id'] for r in unidades})
    report.append(f"Unidades: {len(unidades)} total, {len(novas_unidades)} novas")

    # Equipamentos
    eq_cols = ['id','codigo','tipo_equipamento','fabricante','modelo','numero_serie','patrimonio',
               'status','unidade_id','local_atual_nome','cliente_atual','observacoes',
               'contador_mono','contador_color','data_cadastro','ativo']
    equipamentos = dump_table(cur, 'equipamentos', eq_cols, f'equipamentos_{ts}')
    novos_equipamentos = [r for r in equipamentos if r['id'] not in snapshots['equipamentos']]
    if novos_equipamentos:
        with open(os.path.join(EXPORT_DIR, f'equipamentos_novos_{ts}.json'), 'w', encoding='utf-8') as f:
            json.dump(novos_equipamentos, f, ensure_ascii=False, indent=2)
    save_ids(os.path.join(EXPORT_DIR, snapshot_files['equipamentos']), {r['id'] for r in equipamentos})
    report.append(f"Equipamentos: {len(equipamentos)} total, {len(novos_equipamentos)} novos")

    # Movimentacoes
    mov_cols = ['id','equipamento_id','data_movimentacao','origem_local','origem_unidade',
                'destino_local','destino_unidade','tipo_movimento','responsavel','observacoes',
                'contador_mono_anterior','contador_mono_novo','contador_color_anterior','contador_color_novo']
    movimentacoes = dump_table(cur, 'movimentacoes', mov_cols, f'movimentacoes_{ts}')
    novas_mov = [r for r in movimentacoes if r['id'] not in snapshots['movimentacoes']]
    if novas_mov:
        with open(os.path.join(EXPORT_DIR, f'movimentacoes_novas_{ts}.json'), 'w', encoding='utf-8') as f:
            json.dump(novas_mov, f, ensure_ascii=False, indent=2)
    save_ids(os.path.join(EXPORT_DIR, snapshot_files['movimentacoes']), {r['id'] for r in movimentacoes})
    report.append(f"Movimentacoes: {len(movimentacoes)} total, {len(novas_mov)} novas")

    # Historico de defeitos
    def_cols = ['id','equipamento_id','descricao','data_ocorrencia']
    defeitos = dump_table(cur, 'historico_defeitos', def_cols, f'historico_defeitos_{ts}')
    novos_defeitos = [r for r in defeitos if r['id'] not in snapshots['historico_defeitos']]
    if novos_defeitos:
        with open(os.path.join(EXPORT_DIR, f'historico_defeitos_novos_{ts}.json'), 'w', encoding='utf-8') as f:
            json.dump(novos_defeitos, f, ensure_ascii=False, indent=2)
    save_ids(os.path.join(EXPORT_DIR, snapshot_files['historico_defeitos']), {r['id'] for r in defeitos})
    report.append(f"Historico de defeitos: {len(defeitos)} total, {len(novos_defeitos)} novos")

    conn.close()

    print("CARREGAMENTO SEGURO CONCLUIDO")
    print(f"Pasta: {EXPORT_DIR}")
    for r in report:
        print(" -", r)

if __name__ == '__main__':
    main()
