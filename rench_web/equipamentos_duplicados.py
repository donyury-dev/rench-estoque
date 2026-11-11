import re
from datetime import datetime


EXPRESSAO_SERIE = "UPPER(REGEXP_REPLACE(BTRIM(COALESCE(numero_serie, '')), '\\s+', ' ', 'g'))"
INDICE_SERIE_ATIVA = 'uq_equipamentos_numero_serie_ativo'
_PLACEHOLDERS = {
    'SN', 'NA', 'SEMSERIE', 'SEMNSERIE', 'NUMSERIE', 'NUMERODESERIE',
    'NAOINFORMADO', 'NAOIDENTIFICADO', 'DESCONHECIDO',
}
_CAMPOS_FIXOS = {
    'id', 'codigo', 'tipo_equipamento', 'numero_serie', 'status', 'unidade_id',
    'local_atual_nome', 'cliente_atual', 'data_cadastro', 'ativo', 'observacoes',
    'ultima_movimentacao',
}


def normalizar_numero_serie(valor):
    if valor is None:
        return None
    texto = re.sub(r'\s+', ' ', str(valor).strip()).upper()
    if not texto or re.sub(r'[^A-Z0-9]', '', texto) in _PLACEHOLDERS:
        return None
    return texto


def buscar_serie_duplicada(cur, numero_serie, excluir_id=None):
    serie = normalizar_numero_serie(numero_serie)
    if not serie:
        return None
    sql = f"""
        SELECT id, codigo, modelo, local_atual_nome
        FROM equipamentos
        WHERE ativo=1 AND {EXPRESSAO_SERIE}=%s
    """
    params = [serie]
    if excluir_id is not None:
        sql += ' AND id<>%s'
        params.append(excluir_id)
    sql += ' ORDER BY id LIMIT 1'
    cur.execute(sql, params)
    return cur.fetchone()


def mensagem_serie_duplicada(registro):
    identificacao = registro.get('codigo') or f"ID {registro['id']}"
    modelo = registro.get('modelo') or 'equipamento'
    return (
        f"Este número de série já está cadastrado em {identificacao} ({modelo}). "
        'Localize o equipamento existente em vez de cadastrar outro.'
    )


def escolher_registro_principal(registros):
    return max(
        registros,
        key=lambda item: (item.get('ultima_movimentacao') or datetime.min, -item['id']),
    )


def combinar_registros(principal, origens):
    combinado = dict(principal)
    for origem in origens:
        for campo, valor in origem.items():
            if campo in _CAMPOS_FIXOS:
                continue
            if campo in ('contador_mono', 'contador_color'):
                combinado[campo] = max(int(principal.get(campo) or 0), int(combinado.get(campo) or 0), int(valor or 0))
            elif (combinado.get(campo) is None or str(combinado.get(campo)).strip() == '') and valor is not None and str(valor).strip():
                combinado[campo] = valor

    observacoes = []
    for registro in [principal, *origens]:
        texto = (registro.get('observacoes') or '').strip()
        if texto and texto not in observacoes:
            observacoes.append(texto)
    combinado['observacoes'] = '\n\n'.join(observacoes) or None
    return combinado


def unificar_series_duplicadas(db):
    cur = db.cursor()
    cur.execute('SELECT pg_advisory_xact_lock(%s)', (619832704,))
    cur.execute(f"""
        UPDATE equipamentos SET numero_serie=NULL
        WHERE UPPER(REGEXP_REPLACE(UPPER(COALESCE(numero_serie, '')), '[^A-Z0-9]', '', 'g'))
            IN ('SN', 'NA', 'SEMSERIE', 'SEMNSERIE', 'NUMSERIE', 'NUMERODESERIE',
                'NAOINFORMADO', 'NAOIDENTIFICADO', 'DESCONHECIDO')
    """)
    cur.execute(f"""
        SELECT {EXPRESSAO_SERIE} AS serie
        FROM equipamentos
        WHERE ativo=1 AND numero_serie IS NOT NULL AND BTRIM(numero_serie)<>''
        GROUP BY {EXPRESSAO_SERIE}
        HAVING COUNT(*)>1
    """)
    grupos = cur.fetchall()
    unificados = []

    for grupo in grupos:
        cur.execute(f"""
            SELECT e.*, (
                SELECT MAX(CASE
                    WHEN m.data_movimentacao ~ '^\\d{{4}}-\\d{{2}}-\\d{{2}}'
                    THEN m.data_movimentacao::timestamp ELSE NULL END)
                FROM movimentacoes m WHERE m.equipamento_id=e.id
            ) AS ultima_movimentacao
            FROM equipamentos e
            WHERE e.ativo=1 AND {EXPRESSAO_SERIE.replace('numero_serie', 'e.numero_serie')}=%s
            ORDER BY e.id
            FOR UPDATE
        """, (grupo['serie'],))
        registros = cur.fetchall()
        principal = escolher_registro_principal(registros)
        origens = [item for item in registros if item['id'] != principal['id']]
        combinado = combinar_registros(principal, origens)
        combinado['numero_serie'] = normalizar_numero_serie(principal['numero_serie'])

        ignorados = {'id', 'ultima_movimentacao'}
        campos = [campo for campo in combinado if campo not in ignorados]
        cur.execute(
            f"UPDATE equipamentos SET {', '.join(f'{campo}=%s' for campo in campos)} WHERE id=%s",
            [combinado[campo] for campo in campos] + [principal['id']],
        )
        for origem in origens:
            cur.execute('UPDATE movimentacoes SET equipamento_id=%s WHERE equipamento_id=%s', (principal['id'], origem['id']))
            cur.execute('UPDATE historico_defeitos SET equipamento_id=%s WHERE equipamento_id=%s', (principal['id'], origem['id']))
            cur.execute(
                "UPDATE equipamentos SET ativo=0, observacoes=%s WHERE id=%s",
                (f"Registro duplicado unificado ao equipamento {principal.get('codigo') or principal['id']}.", origem['id']),
            )
        unificados.append({
            'serie': grupo['serie'],
            'mantido_id': principal['id'],
            'arquivados_ids': [item['id'] for item in origens],
        })

    cur.execute(f"""
        CREATE UNIQUE INDEX IF NOT EXISTS {INDICE_SERIE_ATIVA}
        ON equipamentos (UPPER(REGEXP_REPLACE(BTRIM(numero_serie), '\\s+', ' ', 'g')))
        WHERE ativo=1 AND numero_serie IS NOT NULL AND BTRIM(numero_serie)<>''
    """)
    db.commit()
    return unificados
