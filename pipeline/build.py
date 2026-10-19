"""Constrói o warehouse SQLite: bronze (CSV bruto) -> silver (tipado e limpo) -> gold (métricas).

Uso: python -m pipeline.build [--dados dados] [--db warehouse/pontua.db]
"""
import argparse
import csv
import hashlib
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

import yaml

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


def check_manifest(dados: Path) -> None:
    with open(ROOT / "MANIFESTO_v1.csv", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            path = dados / row["arquivo"]
            if sha256(path) != row["sha256"]:
                raise SystemExit(f"{row['arquivo']}: SHA-256 diferente do MANIFESTO_v1.csv")


def load_bronze(con: sqlite3.Connection, dados: Path) -> None:
    """Bronze: cópia fiel do CSV, tudo TEXT, string vazia -> NULL, mais colunas de linhagem."""
    loaded_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
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


def build(dados: Path, db: Path) -> Path:
    check_manifest(dados)
    db.parent.mkdir(parents=True, exist_ok=True)
    if db.exists():
        db.unlink()
    con = sqlite3.connect(db)
    try:
        load_bronze(con, dados)
        run_sql_layer(con, "silver")
        run_sql_layer(con, "gold")
        load_catalog(con)
        con.commit()
    finally:
        con.close()
    return db


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dados", default=str(ROOT / "dados"))
    parser.add_argument("--db", default=str(ROOT / "warehouse" / "pontua.db"))
    args = parser.parse_args()
    db = build(Path(args.dados), Path(args.db))
    print(f"warehouse pronto: {db}")


if __name__ == "__main__":
    main()
