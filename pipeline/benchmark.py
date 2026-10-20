"""Benchmark de acurácia: resultados do pipeline x relatório do operador (única referência externa disponível).

O relatório arredonda percentuais para inteiro; consideramos acerto quando |calculado - reportado| <= 0,5 p.p.
Uso: python -m pipeline.benchmark [--db warehouse/pontua.db]
"""
import argparse
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

METRICAS = {
    # métrica: (expressão calculada, expressão reportada, tolerância absoluta)
    "aereas_pct": ("aereas_pct_calculado", "aereas_pct_relatorio", 0.5),
    "varejo_pct": ("varejo_pct_calculado", "varejo_pct_relatorio", 0.5),
    "pix_pct": ("pix_pct_calculado", "pix_pct_relatorio", 0.5),
    "pix_transacoes (todos os status)": ("pix_transacoes_todos_status", "pix_transacoes_relatorio", 0),
    "pix_pontos (todos os status)": ("pix_pontos_todos_status", "pix_pontos_relatorio", 0),
}


def benchmark(con: sqlite3.Connection) -> list[dict]:
    out = []
    for nome, (calc, rep, tol) in METRICAS.items():
        rows = con.execute(f"SELECT mes, {calc}, {rep} FROM gold_conciliacao_operador "
                           f"WHERE {rep} IS NOT NULL ORDER BY mes").fetchall()
        acertos = [m for m, c, r in rows if abs(c - r) <= tol]
        out.append({"metrica": nome, "meses": len(rows), "acertos": len(acertos),
                    "acuracia_pct": round(100 * len(acertos) / len(rows), 1),
                    "divergentes": [(m, c, r) for m, c, r in rows if abs(c - r) > tol]})
    # pix_reais: o operador não informa o critério; medimos o erro relativo contra os aprovados
    rows = con.execute("SELECT mes, pix_reais_aprovados, pix_reais_relatorio FROM gold_conciliacao_operador "
                       "WHERE pix_reais_relatorio IS NOT NULL ORDER BY mes").fetchall()
    erros = [round(100 * abs(c - r) / r, 2) for _, c, r in rows]
    out.append({"metrica": "pix_reais (aprovados) erro relativo %", "meses": len(rows),
                "acertos": sum(e <= 1 for e in erros), "acuracia_pct": round(100 * sum(e <= 1 for e in erros) / len(rows), 1),
                "divergentes": [(m, e) for (m, _, _), e in zip(rows, erros) if e > 1], "erros_pct": erros})
    return out


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", default=str(ROOT / "warehouse" / "pontua.db"))
    args = parser.parse_args()
    for r in benchmark(sqlite3.connect(args.db)):
        print(r)


if __name__ == "__main__":
    main()
