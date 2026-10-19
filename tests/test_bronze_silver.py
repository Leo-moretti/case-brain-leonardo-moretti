"""Integridade de carga, chaves e regras de limpeza."""
import csv

import pytest

from conftest import ROOT, one

MANIFEST = list(csv.DictReader(open(ROOT / "MANIFESTO_v1.csv", encoding="utf-8")))


@pytest.mark.parametrize("row", MANIFEST, ids=lambda r: r["arquivo"])
def test_bronze_row_count_matches_manifest(con, row):
    tabela = "bronze_" + row["arquivo"].removesuffix(".csv")
    assert one(con, f"SELECT COUNT(*) FROM {tabela}") == int(row["linhas"])


@pytest.mark.parametrize("tabela,chave", [
    ("silver_orders", "order_id"),
    ("silver_order_items", "order_item_id"),
    ("silver_points_ledger", "movement_id"),
    ("silver_cards", "account_id"),
    ("gold_fct_resgate", "order_item_id"),
    ("gold_dim_usuario", "user_id"),
    ("gold_metas_mensal", "mes"),
    ("gold_pontos_mensal", "mes"),
    ("gold_conciliacao_operador", "mes"),
    ("gold_campanha_pix", "grupo"),
])
def test_primary_key_unique_not_null(con, tabela, chave):
    assert one(con, f"SELECT COUNT(*) FROM {tabela} WHERE {chave} IS NULL") == 0
    assert one(con, f"SELECT COUNT(*) - COUNT(DISTINCT {chave}) FROM {tabela}") == 0


def test_resgates_mensal_grain(con):
    assert one(con, "SELECT COUNT(*) - COUNT(DISTINCT mes || modalidade) FROM gold_resgates_mensal") == 0


def test_user_resolved_for_every_order(con):
    assert one(con, "SELECT COUNT(*) FROM silver_orders WHERE user_id IS NULL") == 0


def test_crm_user_resolved_via_device(con):
    assert one(con, "SELECT COUNT(*) FROM silver_crm_events WHERE user_id IS NULL") == 0


def test_device_maps_to_single_user(con):
    assert one(con, "SELECT COUNT(*) FROM (SELECT device_id FROM bronze_crm_events WHERE user_id IS NOT NULL "
                    "GROUP BY 1 HAVING COUNT(DISTINCT user_id) > 1)") == 0


def test_every_item_has_order(con):
    assert one(con, "SELECT COUNT(*) FROM silver_order_items WHERE order_status IS NULL") == 0


def test_ledger_accounts_exist_in_cards(con):
    assert one(con, "SELECT COUNT(*) FROM silver_points_ledger l LEFT JOIN silver_cards c USING (account_id) "
                    "WHERE c.account_id IS NULL") == 0


def test_one_most_recent_card_per_user(con):
    assert one(con, "SELECT COUNT(*) FROM (SELECT user_id FROM silver_cards GROUP BY 1 "
                    "HAVING SUM(is_most_recent) <> 1)") == 0


def test_every_operation_code_known(con):
    assert one(con, "SELECT COUNT(*) FROM silver_points_ledger WHERE operation_name IS NULL") == 0


def test_no_unmapped_modalidade(con):
    assert one(con, "SELECT COUNT(*) FROM silver_order_items WHERE modalidade = 'OUTRO'") == 0


def test_compra_pontos_excluded_from_resgates(con):
    assert one(con, "SELECT COUNT(*) FROM gold_fct_resgate WHERE product_type = 'COMPRA_PONTOS'") == 0
    assert one(con, "SELECT COUNT(*) FROM gold_fct_resgate WHERE pontos IS NULL") == 0
