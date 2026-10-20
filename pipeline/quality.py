"""Executa os guardrails de qualidade definidos em quality/checks.yml, camada a camada."""
import sqlite3
from dataclasses import asdict, dataclass
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
CHECKS = ROOT / "quality" / "checks.yml"


@dataclass
class Resultado:
    run_id: str
    check: str
    camada: str
    severidade: str
    descricao: str
    valor: float | None
    regra: str
    status: str  # ok | falha | erro


class QualidadeBloqueante(Exception):
    def __init__(self, falhas: list[Resultado]):
        self.falhas = falhas
        super().__init__("checks bloqueantes falharam: " + ", ".join(f.check for f in falhas))


def load_spec(path: Path = CHECKS) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _regra(check: dict) -> tuple[str, callable]:
    if "igual" in check:
        return f"= {check['igual']}", lambda v: v == check["igual"]
    if "max" in check:
        return f"<= {check['max']}", lambda v: v <= check["max"]
    if "min" in check:
        return f">= {check['min']}", lambda v: v >= check["min"]
    raise ValueError(f"check {check['id']} sem regra (igual/max/min)")


def run_contracts(con: sqlite3.Connection, spec: dict, run_id: str) -> list[Resultado]:
    """Contrato de schema: colunas do CSV (na bronze) iguais às esperadas, na mesma ordem."""
    out = []
    for tabela, esperadas in spec["contratos"].items():
        cols = [r[1] for r in con.execute(f"PRAGMA table_info(bronze_{tabela})")]
        reais = [c for c in cols if not c.startswith("_")]
        ok = reais == esperadas
        diff = sorted(set(reais) ^ set(esperadas)) or (["ordem"] if not ok else [])
        out.append(Resultado(run_id, f"contrato_{tabela}", "bronze", "bloqueante",
                             f"Colunas de {tabela}.csv" + ("" if ok else f" divergem: {', '.join(diff)}"),
                             len(diff), "= 0", "ok" if ok else "falha"))
    return out


def run_layer(con: sqlite3.Connection, spec: dict, camada: str, run_id: str) -> list[Resultado]:
    out = []
    for check in (c for c in spec["checks"] if c["camada"] == camada):
        regra, passa = _regra(check)
        try:
            valor = con.execute(check["sql"]).fetchone()[0]
            status = "ok" if valor is not None and passa(valor) else "falha"
        except sqlite3.Error as e:
            valor, status = None, "erro"
            check = {**check, "descricao": f"{check['descricao']} [erro SQL: {e}]"}
        out.append(Resultado(run_id, check["id"], camada, check["severidade"], check["descricao"], valor, regra, status))
    return out


def notify_and_gate(resultados: list[Resultado], notifier) -> None:
    """Alerta falhas de bloqueante/alerta e interrompe se houver bloqueante."""
    for r in resultados:
        if r.status != "ok" and r.severidade in ("bloqueante", "alerta"):
            notifier.send(asdict(r))
    bloqueantes = [r for r in resultados if r.status != "ok" and r.severidade == "bloqueante"]
    if bloqueantes:
        raise QualidadeBloqueante(bloqueantes)


def persist(con: sqlite3.Connection, resultados: list[Resultado], executado_em: str) -> None:
    con.execute("""CREATE TABLE IF NOT EXISTS dq_resultados (
        run_id TEXT, executado_em TEXT, check_id TEXT, camada TEXT, severidade TEXT,
        descricao TEXT, valor REAL, regra TEXT, status TEXT)""")
    con.executemany(
        "INSERT INTO dq_resultados VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        [(r.run_id, executado_em, r.check, r.camada, r.severidade, r.descricao, r.valor, r.regra, r.status)
         for r in resultados],
    )
