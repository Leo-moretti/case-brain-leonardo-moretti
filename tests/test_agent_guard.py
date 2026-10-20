"""O agente só pode ler a camada gold, com uma única instrução SELECT."""
import pytest

from pathlib import Path

from agent.core import DadoIndividualBloqueado, guard_identifiers, run_sql, validate_sql


@pytest.mark.parametrize("sql", [
    "SELECT mes, aereas_pct FROM gold_metas_mensal",
    "WITH x AS (SELECT * FROM gold_fct_resgate) SELECT COUNT(*) FROM x",
    "select a.mes from gold_metas_mensal a join gold_pontos_mensal b on a.mes = b.mes;",
    "SELECT check_id, status FROM dq_resultados WHERE status <> 'ok'",
])
def test_allows_gold_selects(sql):
    assert validate_sql(sql)


@pytest.mark.parametrize("sql", [
    "DROP TABLE gold_metas_mensal",
    "SELECT * FROM bronze_orders",
    "SELECT * FROM silver_crm_events",
    "SELECT 1; DELETE FROM gold_metas_mensal",
    "UPDATE gold_metas_mensal SET aereas_pct = 0",
    "SELECT * FROM gold_metas_mensal WHERE 1 = (SELECT 1 FROM sqlite_master)",
])
def test_blocks_everything_else(sql):
    with pytest.raises(ValueError):
        validate_sql(sql)


# guarda de dado individual: roda contra o warehouse construído pela fixture `con`
@pytest.fixture
def agent_db(con, monkeypatch):
    db = con.execute("PRAGMA database_list").fetchone()[2]
    monkeypatch.setattr("agent.core.DB", Path(db))


@pytest.mark.parametrize("sql", [
    "SELECT user_id, SUM(pontos) FROM gold_fct_resgate GROUP BY 1 ORDER BY 2 DESC LIMIT 10",
    "SELECT user_id AS cliente FROM gold_dim_usuario LIMIT 5",          # alias não burla
    "SELECT CAST(order_id AS TEXT) || '' AS x FROM gold_fct_resgate LIMIT 3",
])
def test_blocks_individual_identifiers(agent_db, sql):
    cols, rows = run_sql(validate_sql(sql))
    with pytest.raises(DadoIndividualBloqueado):
        guard_identifiers(cols, rows)


@pytest.mark.parametrize("sql", [
    "SELECT COUNT(DISTINCT user_id) FROM gold_fct_resgate WHERE modalidade = 'PIX'",
    "SELECT COUNT(*) FROM (SELECT user_id FROM gold_fct_resgate WHERE modalidade = 'PIX' GROUP BY 1 HAVING COUNT(*) > 3)",
    "SELECT mes, pontos_total FROM gold_metas_mensal",
])
def test_allows_aggregates(agent_db, sql):
    cols, rows = run_sql(validate_sql(sql))
    guard_identifiers(cols, rows)


def test_audit_trail_records_blocked_and_answered(agent_db, monkeypatch, tmp_path):
    import json

    import agent.core as core

    log = tmp_path / "auditoria.jsonl"
    monkeypatch.setattr(core, "AUDIT_LOG", log)
    respostas = iter([
        '{"acao": "sql", "sql": "SELECT user_id, COUNT(*) FROM gold_fct_resgate GROUP BY 1 LIMIT 10"}',
        '{"acao": "sql", "sql": "SELECT varejo_pct FROM gold_metas_mensal WHERE mes = \'2026-09\'"}',
        "- Varejo em set/26: 12,95%",
    ])
    monkeypatch.setattr(core, "llm", lambda *a, **k: next(respostas))

    bloqueada = core.ask("top 10 clientes")
    ok = core.ask("varejo em setembro")

    assert bloqueada["status"] == "bloqueado_dado_individual" and "linhas" in bloqueada and bloqueada["linhas"] == []
    assert ok["status"] == "respondido" and "não contábeis" in ok["resposta"]
    regs = [json.loads(x) for x in log.read_text().splitlines()]
    assert [r["status"] for r in regs] == ["bloqueado_dado_individual", "respondido"]
    assert all(r["versao_dados"] and r["modelo"] and r["ts"] for r in regs)
    assert regs[1]["resultado_sha256"] and regs[1]["sql"].startswith("SELECT varejo_pct")
