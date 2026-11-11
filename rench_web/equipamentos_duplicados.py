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

_MARCAS_MODELO = (
    'OKI', 'CANON', 'EPSON', 'HP', 'LEXMARK', 'BROTHER', 'SAMSUNG', 'DELL',
    'LENOVO', 'PANASONIC', 'KYOCERA', 'RICOH', 'XEROX', 'TOSHIBA', 'SHARP',
    'ZEBRA', 'ELGIN', 'POSITIVO',
)


def normalizar_modelo(valor):
    """Remove a marca do início do modelo para comparar cadastros.

    'OKI ES4172' e 'ES4172' descrevem o mesmo equipamento, apenas escritos
    de forma diferente em cadastros distintos.
    """
    if valor is None:
        return ''
    texto = re.sub(r'\s+', ' ', str(valor).strip().upper())
    mudou = True
    while mudou:
        mudou = False
        for marca in _MARCAS_MODELO:
            if texto.startswith(marca + ' '):
                texto = texto[len(marca):].strip()
                mudou = True
    return texto


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
    cur.execute("""
        CREATE TABLE IF NOT EXISTS equipamentos_unificacoes (
            id BIGSERIAL PRIMARY KEY,
            principal_id INTEGER NOT NULL,
            origem_id INTEGER NOT NULL,
            registro_principal JSONB NOT NULL,
            registro_origem JSONB NOT NULL,
            movimentacoes_ids JSONB NOT NULL,
            defeitos_ids JSONB NOT NULL,
            criado_em TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)
    cur.execute('ALTER TABLE equipamentos_unificacoes ENABLE ROW LEVEL SECURITY')
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
        if not normalizar_numero_serie(grupo['serie']):
            continue
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
        if len(registros) < 2:
            continue
        # Equipamentos de modelos ou tipos diferentes que dividem a série são
        # aparelhos distintos: ficam de fora e seguem para revisão manual.
        if any(not str(registros[0].get(campo) or '').strip() for campo in ('tipo_equipamento', 'modelo', 'local_atual_nome')):
            continue
        if len({str(item.get('tipo_equipamento') or '').strip().upper() for item in registros}) > 1:
            continue
        if len({str(item.get('status') or '').strip().upper() for item in registros}) > 1:
            continue
        modelos_normalizados = {normalizar_modelo(item.get('modelo')) for item in registros}
        if len(modelos_normalizados) > 1 or not next(iter(modelos_normalizados)):
            continue
        # Local, unidade e cliente podem divergir: é o padrão de um
        # equipamento transferido e cadastrado novamente no novo destino.
        # O registro com a movimentação mais recente representa o local atual.
        principal = escolher_registro_principal(registros)
        origens = [item for item in registros if item['id'] != principal['id']]
        for origem in origens:
            cur.execute("""
                INSERT INTO equipamentos_unificacoes
                    (principal_id, origem_id, registro_principal, registro_origem, movimentacoes_ids, defeitos_ids)
                SELECT p.id, o.id, to_jsonb(p), to_jsonb(o),
                    COALESCE((SELECT jsonb_agg(id) FROM movimentacoes WHERE equipamento_id=o.id), '[]'::jsonb),
                    COALESCE((SELECT jsonb_agg(id) FROM historico_defeitos WHERE equipamento_id=o.id), '[]'::jsonb)
                FROM equipamentos p, equipamentos o WHERE p.id=%s AND o.id=%s
            """, (principal['id'], origem['id']))
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
            cur.execute('UPDATE equipamentos SET ativo=0 WHERE id=%s', (origem['id'],))
        unificados.append({
            'serie': grupo['serie'],
            'mantido_id': principal['id'],
            'arquivados_ids': [item['id'] for item in origens],
        })

    cur.execute("""
        CREATE OR REPLACE FUNCTION proteger_numero_serie_equipamento() RETURNS trigger AS $$
        DECLARE serie TEXT;
        BEGIN
            IF NEW.ativo IS DISTINCT FROM 1 THEN
                RETURN NEW;
            END IF;
            serie := UPPER(REGEXP_REPLACE(BTRIM(COALESCE(NEW.numero_serie, '')), '\\s+', ' ', 'g'));
            IF serie = '' OR REGEXP_REPLACE(serie, '[^A-Z0-9]', '', 'g') IN
                ('SN', 'NA', 'SEMSERIE', 'SEMNSERIE', 'NUMSERIE', 'NUMERODESERIE',
                 'NAOINFORMADO', 'NAOIDENTIFICADO', 'DESCONHECIDO') THEN
                RETURN NEW;
            END IF;
            IF TG_OP = 'UPDATE' THEN
                IF OLD.ativo=1 AND UPPER(REGEXP_REPLACE(BTRIM(COALESCE(OLD.numero_serie, '')), '\\s+', ' ', 'g'))=serie THEN
                    RETURN NEW;
                END IF;
            END IF;
            PERFORM pg_advisory_xact_lock(hashtextextended('equipamento_serie:' || serie, 0));
            IF EXISTS (
                SELECT 1 FROM equipamentos e
                WHERE e.ativo=1 AND e.id IS DISTINCT FROM NEW.id
                  AND UPPER(REGEXP_REPLACE(BTRIM(COALESCE(e.numero_serie, '')), '\\s+', ' ', 'g'))=serie
            ) THEN
                RAISE EXCEPTION 'Este número de série já está cadastrado em outro equipamento ativo.'
                    USING ERRCODE='23505', CONSTRAINT='uq_equipamentos_numero_serie_ativo';
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql
    """)
    cur.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname='trg_equipamento_serie_unica'
                           AND tgrelid='equipamentos'::regclass AND NOT tgisinternal) THEN
                CREATE TRIGGER trg_equipamento_serie_unica
                BEFORE INSERT OR UPDATE OF numero_serie, ativo ON equipamentos
                FOR EACH ROW EXECUTE FUNCTION proteger_numero_serie_equipamento();
            END IF;
        END;
        $$
    """)
    db.commit()
    return unificados
