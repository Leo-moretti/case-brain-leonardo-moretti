"""Garante que os números da apresentação estão certos: conciliações entre fontes e valores de referência."""
import pytest

from conftest import one


def test_ledger_resgate_reconciles_with_items(con):
    ledger = one(con, "SELECT -SUM(points) FROM silver_points_ledger WHERE operation_code = 2")
    itens = one(con, "SELECT SUM(paid_points) FROM silver_order_items WHERE status IN ('APROVADO', 'ESTORNADO')")
    assert ledger == itens == 323_423_650


def test_ledger_estorno_reconciles_with_items(con):
    ledger = one(con, "SELECT SUM(points) FROM silver_points_ledger WHERE operation_code = 14")
    itens = one(con, "SELECT SUM(CASE WHEN status = 'ESTORNADO' THEN paid_points ELSE 0 END) "
                     "+ SUM(refunded_points) FROM silver_order_items")
    assert ledger == itens


def test_redeemed_points_resgate_matches_paid_points(con):
    assert one(con, """
        SELECT COUNT(*) FROM silver_order_items i
        JOIN (SELECT order_item_id, SUM(points) p FROM silver_redeemed_points
              WHERE movement_type = 'RESGATE' GROUP BY 1) r USING (order_item_id)
        WHERE -r.p <> i.paid_points""") == 0


def test_reserva_nets_to_zero(con):
    assert one(con, "SELECT COUNT(*) FROM (SELECT order_item_id FROM silver_redeemed_points "
                    "WHERE movement_type IN ('RESERVA', 'CANCELADO_RESERVA') GROUP BY 1 HAVING SUM(points) <> 0)") == 0


def test_mensal_totals_match_fact(con):
    assert one(con, "SELECT SUM(pontos_aprovados) FROM gold_resgates_mensal") == \
        one(con, "SELECT SUM(pontos) FROM gold_fct_resgate WHERE status = 'APROVADO'")
    assert one(con, "SELECT SUM(pontos_total) FROM gold_metas_mensal") == \
        one(con, "SELECT SUM(pontos_aprovados) FROM gold_resgates_mensal")


def test_metas_shares_sum_to_100(con):
    assert one(con, "SELECT MAX(ABS(aereas_pct + varejo_pct + pix_pct - 100)) FROM gold_metas_mensal") < 0.05


def test_saldo_acumulado_equals_ledger_sum(con):
    assert one(con, "SELECT saldo_acumulado FROM gold_pontos_mensal ORDER BY mes DESC LIMIT 1") == \
        one(con, "SELECT SUM(points) FROM silver_points_ledger") == 377_723_737


def test_pix_rate_is_always_0019(con):
    assert one(con, "SELECT COUNT(*) FROM gold_fct_resgate WHERE modalidade = 'PIX' "
                    "AND ABS(valor_produto_reais / pontos - 0.019) > 0.00001") == 0


def test_pix_starts_on_launch_date(con):
    assert one(con, "SELECT MIN(created_date) FROM gold_fct_resgate WHERE modalidade = 'PIX'") == "2026-05-27"


def test_operator_pix_points_use_all_statuses(con):
    # explica o R$ 0,016: o relatório soma pontos de todos os status
    assert one(con, "SELECT COUNT(*) FROM gold_conciliacao_operador WHERE pix_pontos_relatorio IS NOT NULL "
                    "AND pix_pontos_relatorio <> pix_pontos_todos_status") == 0
    assert one(con, "SELECT MAX(reais_por_ponto_relatorio) FROM gold_conciliacao_operador") < 0.017


@pytest.mark.parametrize("mes,aereas,varejo,pix", [
    ("2026-04", 80.73, 19.27, 0.0),
    ("2026-06", 56.31, 13.33, 30.36),
    ("2026-09", 59.02, 12.95, 28.03),
])
def test_metas_reference_values(con, mes, aereas, varejo, pix):
    row = con.execute("SELECT aereas_pct, varejo_pct, pix_pct FROM gold_metas_mensal WHERE mes = ?", (mes,)).fetchone()
    assert row == (aereas, varejo, pix)


def test_lote_20260112(con):
    assert con.execute("SELECT COUNT(*), SUM(pontos) FROM gold_fct_resgate WHERE flag_lote_20260112 = 1").fetchone() \
        == (1520, 76_002_100)


def test_campanha_groups_cover_all_users(con):
    assert one(con, "SELECT SUM(usuarios) FROM gold_campanha_pix") == one(con, "SELECT COUNT(*) FROM gold_dim_usuario")
    # campanha conta Pix APROVADO ou ESTORNADO (tentou e efetivou); dim_usuario.usou_pix só APROVADO
    assert one(con, "SELECT SUM(usuarios_pix) FROM gold_campanha_pix") == 2172
    assert one(con, "SELECT SUM(usou_pix) FROM gold_dim_usuario") == 2140


def test_no_new_program_points_expired(con):
    assert one(con, "SELECT valor FROM gold_breakage WHERE metrica = 'expirados_programa_novo_pontos'") == 0


def test_benchmark_against_operator_report(con):
    from pipeline.benchmark import benchmark

    r = {b["metrica"]: b for b in benchmark(con)}
    # percentuais batem com o relatório em todos os meses exceto jun/26, quando o operador mudou de critério
    assert r["varejo_pct"]["acuracia_pct"] == 100.0
    assert [d[0] for d in r["aereas_pct"]["divergentes"]] == ["2026-06"]
    assert [d[0] for d in r["pix_pct"]["divergentes"]] == ["2026-06"]
    assert r["pix_pontos (todos os status)"]["acuracia_pct"] == 100.0
    assert max(r["pix_reais (aprovados) erro relativo %"]["erros_pct"]) < 1


def test_inferred_rules_flagged_for_business_review(con):
    assert one(con, "SELECT COUNT(*) FROM meta_regras_inferidas") >= 10
    assert one(con, "SELECT COUNT(*) FROM meta_regras_inferidas WHERE status NOT IN "
                    "('pendente_validacao_negocio', 'validada', 'rejeitada')") == 0
