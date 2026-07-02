import os
import sys
import sqlite3
import pandas as pd

DB_PATH = os.path.join(os.path.dirname(__file__), "rench_web.db")

DEFAULT_XLSX = r"C:\Users\Kaio\Downloads\UNIDADES DEFINITIVAS SAMIR.xlsx"
FALLBACK_XLSX = r"C:\Users\Kaio\Downloads\UNIDADES_DEFINITIVAS_SAMIR.xlsx"


def escolher_arquivo():
    if len(sys.argv) > 1:
        return sys.argv[1]
    if os.path.exists(DEFAULT_XLSX):
        return DEFAULT_XLSX
    if os.path.exists(FALLBACK_XLSX):
        return FALLBACK_XLSX
    raise FileNotFoundError(
        f"Planilha não encontrada em {DEFAULT_XLSX!r} nem em {FALLBACK_XLSX!r}. "
        "Passe o caminho como argumento."
    )


def montar_endereco(row):
    partes = []
    endereco = str(row.get("endereço") or row.get("endereco") or "").strip()
    if endereco:
        partes.append(endereco)
    numero = row.get("numero")
    if pd.notna(numero) and str(numero).strip():
        partes.append(str(int(float(numero))) if isinstance(numero, (int, float)) else str(numero).strip())
    cidade = str(row.get("cidade") or "").strip()
    estado = str(row.get("estado") or "").strip()
    local = ", ".join(filter(None, [cidade, estado]))
    if local:
        partes.append(local)
    return " - ".join(partes) if partes else ""


def main():
    xlsx_path = escolher_arquivo()
    print(f"Lendo planilha: {xlsx_path}")

    df = pd.read_excel(xlsx_path)
    print(f"Registros lidos da planilha: {len(df)}")

    df = df.drop_duplicates(subset=[df.columns[0]])
    print(f"Registros após remover duplicatas pelo nome: {len(df)}")

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("SELECT nome FROM locais")
    existentes = {row[0].strip().upper() for row in cur.fetchall()}

    inseridos = 0
    ignorados = 0

    for _, row in df.iterrows():
        nome = str(row.get("unidade") or "").strip()
        if not nome:
            ignorados += 1
            continue

        if nome.upper() in existentes:
            print(f"Já existe: {nome}")
            ignorados += 1
            continue

        endereco_completo = montar_endereco(row)

        cur.execute(
            "INSERT INTO locais (nome, tipo, unidades, ativo) VALUES (?, ?, ?, ?)",
            (nome, "cliente", endereco_completo, 1),
        )
        inseridos += 1
        existentes.add(nome.upper())

    conn.commit()
    cur.execute("SELECT COUNT(*) FROM locais")
    total_locais = cur.fetchone()[0]
    conn.close()

    print(f"\nInseridos: {inseridos}")
    print(f"Ignorados (duplicados/vazios): {ignorados}")
    print(f"Total de registros na tabela 'locais': {total_locais}")


if __name__ == "__main__":
    main()
