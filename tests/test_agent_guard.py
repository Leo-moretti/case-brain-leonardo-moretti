"""O agente só pode ler a camada gold, com uma única instrução SELECT."""
import pytest

from agent.core import validate_sql


@pytest.mark.parametrize("sql", [
    "SELECT mes, aereas_pct FROM gold_metas_mensal",
    "WITH x AS (SELECT * FROM gold_fct_resgate) SELECT COUNT(*) FROM x",
    "select a.mes from gold_metas_mensal a join gold_pontos_mensal b on a.mes = b.mes;",
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
