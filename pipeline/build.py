"""Constrói o warehouse SQLite: bronze (CSV bruto) -> silver (tipado e limpo) -> gold (métricas).

Cada camada passa pelos guardrails de quality/checks.yml. O build escreve num arquivo temporário e só
substitui o warehouse publicado se nenhum check bloqueante falhar: dashboard e agente nunca leem dados quebrados.

Uso: python -m pipeline.build [--dados dados] [--db warehouse/pontua.db]
"""
import argparse
import csv
import hashlib
import json
import os
import sqlite3
import sys
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

import yaml

from pipeline import quality
from pipeline.alerts import get_notifier

ROOT = Path(__file__).resolve().parent.parent
SQL_DIR = ROOT / "sql"
CATALOG = ROOT / "catalog" / "gold.yml"

SOURCES = [
    "orders", "order_items", "carts", "points_ledger", "dim_operation",
    "cards", "redeemed_points", "crm_events", "relatorio_mensal_cliente",
]


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def check_manifest(dados: Path, run_id: str) -> list[quality.Resultado]:
    """Arquivo ausente bloqueia; hash diferente do manifesto é alerta (nova carga legítima ou arquivo alterado)."""
    out = []
    with open(ROOT / "MANIFESTO_v1.csv", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            path = dados / row["arquivo"]
            if not path.exists():
                out.append(quality.Resultado(run_id, f"arquivo_{row['arquivo']}", "entrada", "bloqueante",
                                             f"{row['arquivo']} ausente", None, "existe", "falha"))
                continue
            igual = sha256(path) == row["sha256"]
            out.append(quality.Resultado(run_id, f"manifesto_{row['arquivo']}", "entrada", "alerta",
                                         f"SHA-256 de {row['arquivo']} " + ("igual ao" if igual else "diferente do")
                                         + " MANIFESTO_v1", int(not igual), "= 0", "ok" if igual else "falha"))
    return out


def load_bronze(con: sqlite3.Connection, dados: Path, loaded_at: str) -> None:
    """Bronze: cópia fiel do CSV, tudo TEXT, string vazia -> NULL, mais colunas de linhagem."""
    for name in SOURCES:
        path = dados / f"{name}.csv"
        with open(path, encoding="utf-8", newline="") as f:
            reader = csv.reader(f)
            header = next(reader)
            cols = ", ".join(f'"{c}" TEXT' for c in header)
            con.execute(f"DROP TABLE IF EXISTS bronze_{name}")
            con.execute(
                f"CREATE TABLE bronze_{name} (_row_id INTEGER, {cols}, _source_file TEXT, _loaded_at TEXT)"
            )
            placeholders = ", ".join("?" for _ in range(len(header) + 3))
            rows = (
                (i, *[v if v != "" else None for v in r], path.name, loaded_at)
                for i, r in enumerate(reader, start=1)
            )
            con.executemany(f"INSERT INTO bronze_{name} VALUES ({placeholders})", rows)


def run_sql_layer(con: sqlite3.Connection, layer: str) -> None:
    for path in sorted((SQL_DIR / layer).glob("*.sql")):
        con.executescript(path.read_text(encoding="utf-8"))


def load_catalog(con: sqlite3.Connection) -> None:
    cat = yaml.safe_load(CATALOG.read_text(encoding="utf-8"))
    con.executescript("""
        DROP TABLE IF EXISTS meta_regras;
        DROP TABLE IF EXISTS meta_tabelas;
        DROP TABLE IF EXISTS meta_colunas;
        CREATE TABLE meta_regras (regra TEXT);
        CREATE TABLE meta_tabelas (tabela TEXT PRIMARY KEY, grao TEXT, descricao TEXT);
        CREATE TABLE meta_colunas (tabela TEXT, coluna TEXT, descricao TEXT, PRIMARY KEY (tabela, coluna));
    """)
    con.executemany("INSERT INTO meta_regras VALUES (?)", [(r,) for r in cat["regras_gerais"]])
    for tabela, spec in cat["tabelas"].items():
        con.execute("INSERT INTO meta_tabelas VALUES (?, ?, ?)", (tabela, spec["grao"], spec["descricao"]))
        con.executemany(
            "INSERT INTO meta_colunas VALUES (?, ?, ?)",
            [(tabela, c, d) for c, d in spec["colunas"].items()],
        )


def _historico(db: Path, resultados: list[quality.Resultado], executado_em: str, publicado: bool) -> None:
    with open(db.parent / "dq_historico.jsonl", "a", encoding="utf-8") as f:
        for r in resultados:
            f.write(json.dumps({**asdict(r), "executado_em": executado_em, "publicado": publicado},
                               ensure_ascii=False) + "\n")


def build(dados: Path, db: Path) -> Path:
    db.parent.mkdir(parents=True, exist_ok=True)
    executado_em = datetime.now(timezone.utc).isoformat(timespec="seconds")
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%f")
    notifier = get_notifier(db.parent)
    spec = quality.load_spec()
    tmp = db.with_suffix(".tmp.db")
    tmp.unlink(missing_ok=True)
    resultados: list[quality.Resultado] = []

    con = sqlite3.connect(tmp)
    try:
        etapa = check_manifest(dados, run_id)
        resultados += etapa
        quality.notify_and_gate(etapa, notifier)

        load_bronze(con, dados, executado_em)
        etapa = quality.run_contracts(con, spec, run_id) + quality.run_layer(con, spec, "bronze", run_id)
        resultados += etapa
        quality.notify_and_gate(etapa, notifier)

        for camada in ("silver", "gold"):
            run_sql_layer(con, camada)
            etapa = quality.run_layer(con, spec, camada, run_id)
            resultados += etapa
            quality.notify_and_gate(etapa, notifier)

        load_catalog(con)
        quality.persist(con, resultados, executado_em)
        con.commit()
    except quality.QualidadeBloqueante:
        con.close()
        tmp.unlink(missing_ok=True)
        _historico(db, resultados, executado_em, publicado=False)
        raise
    con.close()
    os.replace(tmp, db)  # publicação atômica
    _historico(db, resultados, executado_em, publicado=True)
    return db


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dados", default=str(ROOT / "dados"))
    parser.add_argument("--db", default=str(ROOT / "warehouse" / "pontua.db"))
    args = parser.parse_args()
    try:
        db = build(Path(args.dados), Path(args.db))
    except quality.QualidadeBloqueante as e:
        print(f"BUILD INTERROMPIDO: {e}. Warehouse publicado anterior mantido.", file=sys.stderr)
        sys.exit(1)
    print(f"warehouse pronto: {db}")


if __name__ == "__main__":
    main()
