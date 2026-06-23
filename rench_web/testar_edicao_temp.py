import sqlite3

from app import app

con = sqlite3.connect("rench_web.db")
con.row_factory = sqlite3.Row
cur = con.cursor()

equipamento = cur.execute(
    "SELECT * FROM equipamentos WHERE tipo_equipamento='impressora' ORDER BY id LIMIT 1"
).fetchone()

if not equipamento:
    raise SystemExit("Nenhuma impressora encontrada para teste.")

equipamento_id = equipamento["id"]
valores_originais = {
    "fabricante": equipamento["fabricante"],
    "modelo": equipamento["modelo"],
    "numero_serie": equipamento["numero_serie"],
    "patrimonio": equipamento["patrimonio"],
    "status": equipamento["status"],
    "unidade_id": equipamento["unidade_id"],
    "local_atual_nome": equipamento["local_atual_nome"],
    "cliente_atual": equipamento["cliente_atual"],
    "observacoes": equipamento["observacoes"],
    "funcao": equipamento["funcao"],
    "tipo_impressao": equipamento["tipo_impressao"],
    "tamanho_papel": equipamento["tamanho_papel"],
    "funcionalidades": equipamento["funcionalidades"],
    "contador_mono": equipamento["contador_mono"],
    "contador_color": equipamento["contador_color"],
}

client = app.test_client()

resposta_get = client.get(f"/equipamento/{equipamento_id}/editar")
print("GET editar:", resposta_get.status_code)

resposta_post = client.post(
    f"/equipamento/{equipamento_id}/editar",
    data={
        "fabricante": equipamento["fabricante"] or "OKI",
        "modelo": equipamento["modelo"] or "OKI ES5112",
        "numero_serie": equipamento["numero_serie"] or "TESTE-EDIT",
        "patrimonio": equipamento["patrimonio"] or "",
        "status": equipamento["status"] or "ativo",
        "unidade_id": str(equipamento["unidade_id"] or ""),
        "local_atual_nome": equipamento["local_atual_nome"] or "",
        "observacoes": "Teste temporario de edicao",
        "funcao": equipamento["funcao"] or "impressora",
        "tipo_impressao": equipamento["tipo_impressao"] or "laser",
        "tamanho_papel": equipamento["tamanho_papel"] or "A4",
        "funcionalidades": equipamento["funcionalidades"] or "Rede",
        "contador_mono": "98765",
        "contador_color": "12",
    },
    follow_redirects=False,
)
print("POST editar:", resposta_post.status_code)

editado = cur.execute(
    "SELECT contador_mono, contador_color FROM equipamentos WHERE id=?",
    (equipamento_id,),
).fetchone()
print("Contadores editados:", dict(editado))

cur.execute(
    """
    UPDATE equipamentos
    SET fabricante=?, modelo=?, numero_serie=?, patrimonio=?, status=?,
        unidade_id=?, local_atual_nome=?, cliente_atual=?, observacoes=?,
        funcao=?, tipo_impressao=?, tamanho_papel=?, funcionalidades=?,
        contador_mono=?, contador_color=?
    WHERE id=?
    """,
    (
        valores_originais["fabricante"],
        valores_originais["modelo"],
        valores_originais["numero_serie"],
        valores_originais["patrimonio"],
        valores_originais["status"],
        valores_originais["unidade_id"],
        valores_originais["local_atual_nome"],
        valores_originais["cliente_atual"],
        valores_originais["observacoes"],
        valores_originais["funcao"],
        valores_originais["tipo_impressao"],
        valores_originais["tamanho_papel"],
        valores_originais["funcionalidades"],
        valores_originais["contador_mono"],
        valores_originais["contador_color"],
        equipamento_id,
    ),
)
con.commit()
print("Valores originais restaurados.")
con.close()