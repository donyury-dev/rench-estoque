#!/usr/bin/env python3
"""Exporta dados públicos do Supabase e valida os artefatos do backup."""

import argparse
import hashlib
import json
import os
import re
import subprocess
import tempfile
import urllib.error
import urllib.request
import uuid
from collections import Counter
from datetime import date, datetime, time
from decimal import Decimal
from pathlib import Path, PurePosixPath
from urllib.parse import quote, unquote, urlparse, urlunparse

import psycopg2
import psycopg2.extras
from psycopg2 import sql

URL_RE = re.compile(r"https?://[^\s<>\"']+", re.IGNORECASE)
PUBLIC_PREFIX = "/storage/v1/object/public/"
STORAGE_PREFIX = "/storage/v1/object/"
INVENTORY_NAME = "inventario.json"
CHECKSUMS_NAME = "SHA256SUMS"
ATTACHMENTS_NAME = "anexos-manifesto.json"


class AttachmentSkipped(Exception):
    pass


def sha256_file(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def json_default(value):
    if isinstance(value, memoryview):
        value = value.tobytes()
    if isinstance(value, bytes):
        return "\\x" + value.hex()
    if isinstance(value, (date, datetime, time, Decimal, uuid.UUID)):
        return str(value)
    return str(value)


def write_json(path, value):
    with path.open("w", encoding="utf-8") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2, default=json_default)
        handle.write("\n")


def attachment_entry(raw_url, project_ref):
    """Reconhece somente URLs do Storage do projeto; remove query e fragmento."""
    try:
        parsed = urlparse(raw_url.rstrip(".,);"))
        hostname = (parsed.hostname or "").lower()
        port = parsed.port
    except ValueError:
        return None
    if hostname != f"{project_ref}.supabase.co" or STORAGE_PREFIX not in parsed.path:
        return None

    clean_url = urlunparse((parsed.scheme.lower(), hostname, parsed.path, "", "", ""))
    entry = {
        "url": clean_url,
        "bucket": None,
        "object_path": None,
        "path": None,
        "status": "pendente",
        "references": [],
    }
    if parsed.username or parsed.password or port not in (None, 443):
        entry.update(status="ignorado", reason="url_com_credenciais_ou_porta_nao_suportada")
        return entry
    if parsed.scheme.lower() != "https":
        entry.update(status="ignorado", reason="somente_https")
        return entry
    mode, mode_separator, object_reference = parsed.path[len(STORAGE_PREFIX):].partition("/")
    bucket, separator, object_path = object_reference.partition("/")
    if not mode_separator or not bucket or not separator or not object_path:
        entry.update(status="ignorado", reason="caminho_de_objeto_invalido")
        return entry

    bucket = unquote(bucket)
    object_path = unquote(object_path)
    suffix = PurePosixPath(object_path).suffix
    if not re.fullmatch(r"\.[A-Za-z0-9]{1,10}", suffix):
        suffix = ""
    digest = hashlib.sha256(clean_url.encode("utf-8")).hexdigest()
    entry.update(
        bucket=bucket,
        object_path=object_path,
        path=f"anexos/{quote(bucket, safe='')}/{digest}{suffix}",
    )
    if mode != "public":
        entry.update(status="ignorado", reason="storage_privado_ou_url_assinada")
    return entry


def collect_attachments(value, table, row_index, json_path, project_ref, attachments):
    if isinstance(value, dict):
        for key, item in value.items():
            collect_attachments(item, table, row_index, f"{json_path}.{key}", project_ref, attachments)
    elif isinstance(value, (list, tuple)):
        for index, item in enumerate(value):
            collect_attachments(item, table, row_index, f"{json_path}[{index}]", project_ref, attachments)
    elif isinstance(value, str):
        for match in URL_RE.finditer(value):
            entry = attachment_entry(match.group(0), project_ref)
            if entry is None:
                continue
            existing = attachments.setdefault(entry["url"], entry)
            existing["references"].append(
                {"table": table, "row_index": row_index, "json_path": json_path}
            )


def safe_http_error(exc):
    if isinstance(exc, urllib.error.HTTPError):
        return f"HTTP_{exc.code}"
    if isinstance(exc, urllib.error.URLError):
        return f"rede_{type(exc.reason).__name__}"
    return type(exc).__name__


def download_attachment(entry, outdir, max_bytes):
    target = outdir / entry["path"]
    target.parent.mkdir(parents=True, exist_ok=True)
    partial = target.with_name(target.name + ".part")
    try:
        url = entry["url"]
        headers = {"User-Agent": "rench-backup/1.0"}
        if entry["status"] == "ignorado" and entry["reason"] == "storage_privado_ou_url_assinada":
            service_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "").strip()
            if not service_key:
                raise RuntimeError("anexo privado requer SUPABASE_SERVICE_ROLE_KEY no GitHub Actions")
            host = urlparse(url).hostname
            url = f"https://{host}/storage/v1/object/{quote(entry['bucket'], safe='')}/{quote(entry['object_path'], safe='/')}"
            headers.update(Authorization=f"Bearer {service_key}", apikey=service_key)
        request = urllib.request.Request(url, headers=headers, method="GET")
        digest = hashlib.sha256()
        total = 0
        with urllib.request.urlopen(request, timeout=30) as response:
            if urlparse(response.geturl()).scheme != "https":
                raise AttachmentSkipped("redirecionamento_sem_https")
            length = response.headers.get("Content-Length")
            if length and int(length) > max_bytes:
                raise AttachmentSkipped("arquivo_excede_limite")
            with partial.open("xb") as handle:
                while True:
                    chunk = response.read(1024 * 1024)
                    if not chunk:
                        break
                    total += len(chunk)
                    if total > max_bytes:
                        raise AttachmentSkipped("arquivo_excede_limite")
                    handle.write(chunk)
                    digest.update(chunk)
        partial.replace(target)
        entry.update(status="baixado", bytes=total, sha256=digest.hexdigest())
        entry.pop("reason", None)
    except AttachmentSkipped as exc:
        entry.update(status="ignorado", reason=str(exc))
    except Exception as exc:  # Um anexo antigo/ausente não invalida o backup do banco.
        entry.update(status="erro", reason=safe_http_error(exc))
        print(f"Anexo não baixado ({entry['reason']}); o backup continuará.")
    finally:
        if partial.exists():
            partial.unlink()


def all_files(outdir):
    return {
        path.relative_to(outdir).as_posix(): path
        for path in outdir.rglob("*")
        if path.is_file() and not path.is_symlink()
    }


def write_inventory(outdir, project_ref, dump_name, tables, attachment_summary):
    files = []
    for relative, path in sorted(all_files(outdir).items()):
        if relative in (INVENTORY_NAME, CHECKSUMS_NAME):
            continue
        files.append({"path": relative, "bytes": path.stat().st_size, "sha256": sha256_file(path)})

    inventory = {
        "format_version": 1,
        "generated_at": datetime.utcnow().replace(microsecond=0).isoformat() + "Z",
        "project_ref": project_ref,
        "dump": dump_name,
        "tables": tables,
        "attachments": attachment_summary,
        "files": files,
    }
    write_json(outdir / INVENTORY_NAME, inventory)

    checksum_files = all_files(outdir)
    with (outdir / CHECKSUMS_NAME).open("w", encoding="utf-8") as handle:
        for relative, path in sorted(checksum_files.items()):
            if relative != CHECKSUMS_NAME:
                handle.write(f"{sha256_file(path)}  {relative}\n")


def export_backup(outdir, project_ref, dump_name, max_bytes):
    dump_path = outdir / dump_name
    if not dump_path.is_file() or dump_path.stat().st_size == 0:
        raise ValueError("Dump ausente ou vazio; a exportação foi interrompida.")

    attachments = {}
    tables = []
    conn = psycopg2.connect(
        os.environ["SUPABASE_DB_URL"],
        application_name="rench_backup_readonly",
        connect_timeout=30,
    )
    try:
        conn.set_session(readonly=True, isolation_level="REPEATABLE READ", autocommit=False)
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
                ORDER BY table_name
                """
            )
            table_names = [row[0] for row in cursor.fetchall()]

        for table in table_names:
            relative = quote(table, safe="") + ".json"
            row_count = 0
            query = sql.SQL("SELECT * FROM {}.{}").format(
                sql.Identifier("public"), sql.Identifier(table)
            )
            with conn.cursor(
                name="rench_backup_export", cursor_factory=psycopg2.extras.RealDictCursor
            ) as cursor:
                cursor.itersize = 1000
                cursor.execute(query)
                with (outdir / relative).open("w", encoding="utf-8") as handle:
                    handle.write("[\n")
                    for row in cursor:
                        if row_count:
                            handle.write(",\n")
                        handle.write("  ")
                        json.dump(row, handle, ensure_ascii=False, default=json_default)
                        collect_attachments(row, table, row_count, "$", project_ref, attachments)
                        row_count += 1
                    handle.write("\n]\n")
            tables.append({"name": table, "file": relative, "rows": row_count})
            print(f"{table}: {row_count} registros")
    finally:
        conn.close()

    for entry in attachments.values():
        if entry["status"] == "pendente" or entry.get("reason") == "storage_privado_ou_url_assinada":
            download_attachment(entry, outdir, max_bytes)

    attachment_summary = dict(sorted(Counter(
        entry["status"] for entry in attachments.values()
    ).items()))
    manifest = {
        "format_version": 1,
        "generated_at": datetime.utcnow().replace(microsecond=0).isoformat() + "Z",
        "project_ref": project_ref,
        "max_attachment_bytes": max_bytes,
        "summary": attachment_summary,
        "attachments": list(attachments.values()),
    }
    write_json(outdir / ATTACHMENTS_NAME, manifest)

    with (outdir / "RESUMO.md").open("w", encoding="utf-8") as handle:
        handle.write(f"# Backup {outdir.name}\n\n")
        handle.write("| Tabela | Registros | Arquivo |\n|---|---:|---|\n")
        for table in tables:
            handle.write(f"| {table['name']} | {table['rows']} | {table['file']} |\n")
        handle.write("\n## Anexos do Supabase Storage\n\n")
        if attachment_summary:
            for status, count in attachment_summary.items():
                handle.write(f"- {status}: {count}\n")
        else:
            handle.write("Nenhuma URL do Storage do projeto foi encontrada.\n")
        handle.write("\nFalhas e arquivos ignorados estão detalhados em `anexos-manifesto.json`.\n")

    write_inventory(outdir, project_ref, dump_name, tables, attachment_summary)


def resolve_backup_file(outdir, relative):
    pure = PurePosixPath(relative)
    if pure.is_absolute() or ".." in pure.parts:
        raise ValueError(f"Caminho inseguro no inventário: {relative}")
    path = outdir.joinpath(*pure.parts)
    if not path.is_file() or path.is_symlink():
        raise ValueError(f"Artefato ausente ou inválido: {relative}")
    return path


def validate_backup(outdir):
    inventory = json.loads(resolve_backup_file(outdir, INVENTORY_NAME).read_text(encoding="utf-8"))
    actual = all_files(outdir)
    expected_inventory = set(actual) - {INVENTORY_NAME, CHECKSUMS_NAME}
    listed_inventory = {entry["path"] for entry in inventory["files"]}
    if listed_inventory != expected_inventory:
        raise ValueError("Inventário não cobre exatamente os artefatos do backup.")

    for entry in inventory["files"]:
        path = resolve_backup_file(outdir, entry["path"])
        if path.stat().st_size != entry["bytes"] or sha256_file(path) != entry["sha256"]:
            raise ValueError(f"Tamanho ou SHA-256 divergente: {entry['path']}")

    checksum_lines = resolve_backup_file(outdir, CHECKSUMS_NAME).read_text(encoding="utf-8").splitlines()
    checksums = dict(reversed(line.split("  ", 1)) for line in checksum_lines)
    if set(checksums) != set(actual) - {CHECKSUMS_NAME}:
        raise ValueError("SHA256SUMS não cobre exatamente os artefatos esperados.")
    for relative, expected_hash in checksums.items():
        if sha256_file(resolve_backup_file(outdir, relative)) != expected_hash:
            raise ValueError(f"Checksum divergente: {relative}")

    dump_path = resolve_backup_file(outdir, inventory["dump"])
    if dump_path.stat().st_size == 0:
        raise ValueError("Dump vazio.")
    subprocess.run(["pg_restore", "--list", str(dump_path)], check=True, stdout=subprocess.DEVNULL)

    for table in inventory["tables"]:
        rows = json.loads(resolve_backup_file(outdir, table["file"]).read_text(encoding="utf-8"))
        if not isinstance(rows, list) or len(rows) != table["rows"]:
            raise ValueError(f"JSON ou contagem inválida para a tabela {table['name']}.")

    manifest = json.loads(resolve_backup_file(outdir, ATTACHMENTS_NAME).read_text(encoding="utf-8"))
    summary = dict(sorted(Counter(entry["status"] for entry in manifest["attachments"]).items()))
    if summary != manifest["summary"] or summary != inventory["attachments"]:
        raise ValueError("Resumo de anexos divergente.")
    for entry in manifest["attachments"]:
        if entry["status"] == "baixado":
            path = resolve_backup_file(outdir, entry["path"])
            if path.stat().st_size != entry["bytes"] or sha256_file(path) != entry["sha256"]:
                raise ValueError("Anexo baixado não corresponde ao manifesto.")
        elif entry["status"] not in ("erro", "ignorado"):
            raise ValueError("Status de anexo inválido no manifesto.")

    print(
        f"Artefatos válidos: {len(actual)} arquivos, {len(inventory['tables'])} tabelas; "
        f"anexos: {summary or 'nenhum'}."
    )


def checked_restore_url():
    restore_url = os.environ["RESTORE_DB_URL"]
    parsed = urlparse(restore_url)
    if (
        parsed.scheme not in ("postgres", "postgresql")
        or parsed.hostname not in ("localhost", "127.0.0.1", "::1")
        or parsed.path != "/restore_test"
    ):
        raise ValueError("A restauração de teste só permite o banco local restore_test.")
    return restore_url


def prepare_restore_db(restore_url):
    """Cria dependências gerenciadas pelo Supabase somente no banco temporário."""
    conn = psycopg2.connect(restore_url, application_name="rench_restore_test")
    try:
        with conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    DO $do$
                    BEGIN
                        IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'anon') THEN
                            EXECUTE 'CREATE ROLE anon NOLOGIN';
                        END IF;
                        IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'authenticated') THEN
                            EXECUTE 'CREATE ROLE authenticated NOLOGIN';
                        END IF;
                        IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'service_role') THEN
                            EXECUTE 'CREATE ROLE service_role NOLOGIN';
                        END IF;
                    END
                    $do$;
                    CREATE SCHEMA IF NOT EXISTS auth;
                    CREATE TABLE IF NOT EXISTS auth.users (id uuid PRIMARY KEY, email text);
                    CREATE OR REPLACE FUNCTION auth.uid() RETURNS uuid
                        LANGUAGE sql STABLE AS $$ SELECT NULL::uuid $$;
                    CREATE OR REPLACE FUNCTION auth.role() RETURNS text
                        LANGUAGE sql STABLE AS $$ SELECT NULL::text $$;
                    CREATE OR REPLACE FUNCTION auth.jwt() RETURNS jsonb
                        LANGUAGE sql STABLE AS $$ SELECT '{}'::jsonb $$;
                    CREATE SCHEMA IF NOT EXISTS extensions;
                    CREATE EXTENSION IF NOT EXISTS "uuid-ossp" WITH SCHEMA extensions;
                    CREATE EXTENSION IF NOT EXISTS pgcrypto WITH SCHEMA extensions;
                    CREATE EXTENSION IF NOT EXISTS unaccent WITH SCHEMA extensions;
                    ALTER DATABASE restore_test SET search_path TO public, extensions;
                    """
                )
    finally:
        conn.close()


def populate_temporary_auth_users(restore_url):
    """Satisfaz FKs auth.users sem exportar ou consultar o Auth de produção."""
    conn = psycopg2.connect(restore_url, application_name="rench_restore_test")
    try:
        with conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT c.table_name, c.column_name
                    FROM information_schema.columns AS c
                    JOIN information_schema.tables AS t
                      ON t.table_schema = c.table_schema AND t.table_name = c.table_name
                    WHERE c.table_schema = 'public'
                      AND t.table_type = 'BASE TABLE'
                      AND c.data_type = 'uuid'
                    ORDER BY c.table_name, c.column_name
                    """
                )
                uuid_columns = cursor.fetchall()
                for table, column in uuid_columns:
                    cursor.execute(
                        sql.SQL(
                            """
                            INSERT INTO auth.users (id)
                            SELECT DISTINCT {column} FROM {table}
                            WHERE {column} IS NOT NULL
                            ON CONFLICT (id) DO NOTHING
                            """
                        ).format(
                            column=sql.Identifier(column),
                            table=sql.Identifier("public", table),
                        )
                    )
    finally:
        conn.close()


def restore_backup(outdir):
    restore_url = checked_restore_url()
    inventory = json.loads(resolve_backup_file(outdir, INVENTORY_NAME).read_text(encoding="utf-8"))
    dump_path = resolve_backup_file(outdir, inventory["dump"])
    prepare_restore_db(restore_url)

    with tempfile.TemporaryDirectory(prefix="rench-restore-") as tempdir:
        toc = subprocess.run(
            ["pg_restore", "--list", str(dump_path)],
            check=True, capture_output=True, text=True,
        ).stdout
        # O Postgres temporário já possui public; todos os demais objetos são restaurados.
        restore_list = Path(tempdir) / "restore.list"
        with restore_list.open("w", encoding="utf-8") as handle:
            for line in toc.splitlines(keepends=True):
                if re.match(r"^\d+; \d+ \d+ SCHEMA - public(?:\s|$)", line):
                    handle.write(";" + line)
                else:
                    handle.write(line)

        base_command = [
            "pg_restore", f"--dbname={restore_url}", "--no-owner", "--no-privileges",
            "--exit-on-error", "--single-transaction", f"--use-list={restore_list}",
        ]
        subprocess.run(
            base_command + ["--section=pre-data", "--section=data", str(dump_path)], check=True
        )
        # As FKs são criadas na fase post-data, depois de popular o Auth temporário.
        populate_temporary_auth_users(restore_url)
        subprocess.run(base_command + ["--section=post-data", str(dump_path)], check=True)

    conn = psycopg2.connect(restore_url, application_name="rench_restore_test")
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT count(*) FROM information_schema.tables
                WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
                """
            )
            restored_tables = cursor.fetchone()[0]
            if restored_tables < 1:
                raise ValueError("Nenhuma tabela public foi restaurada.")
    finally:
        conn.close()
    print(f"Restauração temporária validada: {restored_tables} tabelas public.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    for command in ("exportar", "validar", "restaurar"):
        sub = subparsers.add_parser(command)
        sub.add_argument("--dir", default=os.environ.get("BACKUP_DIR"))
        if command == "exportar":
            sub.add_argument("--project-ref", default=os.environ.get("SUPABASE_PROJECT_REF"))
            sub.add_argument("--dump-name", default=os.environ.get("DUMP_NAME", "backup.dump"))
            sub.add_argument(
                "--max-bytes", type=int, default=int(os.environ.get("MAX_ATTACHMENT_BYTES", "95000000"))
            )
    args = parser.parse_args()
    if not args.dir:
        parser.error("Informe --dir ou BACKUP_DIR.")
    outdir = Path(args.dir).resolve()
    if args.command == "exportar":
        if not args.project_ref:
            parser.error("Informe --project-ref ou SUPABASE_PROJECT_REF.")
        if args.max_bytes <= 0:
            parser.error("--max-bytes deve ser positivo.")
        export_backup(outdir, args.project_ref, args.dump_name, args.max_bytes)
    elif args.command == "validar":
        validate_backup(outdir)
    else:
        restore_backup(outdir)


if __name__ == "__main__":
    main()
