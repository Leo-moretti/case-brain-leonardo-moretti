"""Exporta só gold_*, dq_* e meta_* para um SQLite pequeno (deploy serverless; bronze/silver não saem do ambiente).

Uso: python -m pipeline.export_gold [--db warehouse/pontua.db] [--out api/pontua_gold.db]
"""
import argparse
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def export(db: Path, out: Path) -> Path:
    out.parent.mkdir(parents=True, exist_ok=True)
    out.unlink(missing_ok=True)
    con = sqlite3.connect(out)
    con.execute("ATTACH DATABASE ? AS src", (str(db),))
    tabelas = [r[0] for r in con.execute(
        "SELECT name FROM src.sqlite_master WHERE type = 'table' "
        "AND (name LIKE 'gold\\_%' ESCAPE '\\' OR name LIKE 'dq\\_%' ESCAPE '\\' OR name LIKE 'meta\\_%' ESCAPE '\\')")]
    for t in tabelas:
        con.execute(f"CREATE TABLE {t} AS SELECT * FROM src.{t}")
    con.commit()
    con.execute("DETACH DATABASE src")
    con.execute("VACUUM")
    con.close()
    return out


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--db", default=str(ROOT / "warehouse" / "pontua.db"))
    p.add_argument("--out", default=str(ROOT / "api" / "pontua_gold.db"))
    a = p.parse_args()
    print(export(Path(a.db), Path(a.out)))
