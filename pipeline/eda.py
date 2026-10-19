"""Reproduz os números citados em docs/EDA.md e na apresentação a partir do warehouse.

Uso: python -m pipeline.eda [--db warehouse/pontua.db]
"""
import argparse
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

CHECKS = {
    "Qualidade: orders.user_id vazio (bronze)":
        "SELECT COUNT(*) FROM bronze_orders WHERE user_id IS NULL",
    "Qualidade: pedidos com 2 itens":
        "SELECT COUNT(*) FROM (SELECT order_id FROM bronze_order_items GROUP BY 1 HAVING COUNT(*) > 1)",
    "Qualidade: itens com status diferente do pedido":
        "SELECT COUNT(*) FROM silver_order_items WHERE status <> order_status",
    "Qualidade: códigos de operação sem movimento":
        "SELECT group_concat(operation_code) FROM bronze_dim_operation d WHERE NOT EXISTS "
        "(SELECT 1 FROM bronze_points_ledger l WHERE l.operation_code = d.operation_code)",
    "Qualidade: itens com 2 linhas RESGATE (pagamento dividido)":
        "SELECT COUNT(*) FROM (SELECT order_item_id FROM silver_redeemed_points WHERE movement_type = 'RESGATE' "
        "GROUP BY 1 HAVING COUNT(*) = 2)",
    "Qualidade: eventos CRM sem user_id (recuperados via device)":
        "SELECT COUNT(*), SUM(user_id IS NOT NULL) FROM silver_crm_events WHERE user_id_from_device = 1",
    "Qualidade: control_group preenchido no CRM":
        "SELECT COUNT(*) FROM silver_crm_events WHERE control_group IS NOT NULL",
    "Qualidade: contas com saldo negativo":
        "SELECT COUNT(*) FROM (SELECT account_id FROM silver_points_ledger GROUP BY 1 HAVING SUM(points) < 0)",
    "Qualidade: contas com expiração de migração sem crédito de migração":
        "SELECT COUNT(DISTINCT account_id) FROM silver_points_ledger e WHERE operation_code = 103 AND NOT EXISTS "
        "(SELECT 1 FROM silver_points_ledger m WHERE m.account_id = e.account_id AND m.operation_code = 100)",
    "Qualidade: valid_until dos créditos de migração":
        "SELECT MIN(valid_until), MAX(valid_until) FROM silver_points_ledger WHERE operation_code = 100",
    "Conciliação: RESGATE ledger x paid_points (aprovado + estornado)":
        "SELECT (SELECT -SUM(points) FROM silver_points_ledger WHERE operation_code = 2), "
        "(SELECT SUM(paid_points) FROM silver_order_items WHERE status IN ('APROVADO','ESTORNADO'))",
    "Lote 12/01/2026: itens, pontos, usuários, % com migração":
        "SELECT COUNT(*), SUM(f.pontos), COUNT(DISTINCT f.user_id), "
        "ROUND(100.0 * SUM(u.tem_saldo_migrado) / COUNT(*), 1) FROM gold_fct_resgate f "
        "JOIN gold_dim_usuario u USING (user_id) WHERE flag_lote_20260112 = 1",
    "Pix: primeiro item, taxa mín/máx R$/ponto":
        "SELECT MIN(created_at), ROUND(MIN(valor_produto_reais / pontos), 4), ROUND(MAX(valor_produto_reais / pontos), 4) "
        "FROM gold_fct_resgate WHERE modalidade = 'PIX'",
    "Pix: usuários e quantos nunca tinham resgatado antes":
        "SELECT COUNT(*), SUM(1 - resgatou_antes_pix) FROM gold_dim_usuario WHERE usou_pix = 1",
    "Pix: % cancelado+inválido x demais modalidades (pós-lançamento)":
        "SELECT modalidade = 'PIX', ROUND(100.0 * SUM(status IN ('CANCELADO','INVALIDO')) / COUNT(*), 1) "
        "FROM gold_fct_resgate WHERE periodo_pix = 'POS_PIX' GROUP BY 1",
    "Metas por mês (aéreas %, varejo %, varejo produto %, pix %, aéreas sem pix %)":
        "SELECT mes, aereas_pct, varejo_pct, varejo_produto_pct, pix_pct, aereas_pct_sem_pix FROM gold_metas_mensal ORDER BY mes",
    "Aéreas % em jan/26 sem o lote":
        "SELECT aereas_pct_sem_lote FROM gold_metas_mensal WHERE mes = '2026-01'",
    "Custo por ponto por modalidade (R$)":
        "SELECT modalidade, ROUND(SUM(custo_pontos_reais) / SUM(pontos_aprovados), 4) FROM gold_resgates_mensal GROUP BY 1",
    "Campanha Pix: adoção por grupo":
        "SELECT grupo, usuarios, usuarios_pix, adocao_pix_pct, resgatadores_previos_pct FROM gold_campanha_pix ORDER BY grupo",
    "Campanha Pix: primeiro envio e Pix antes do envio":
        "SELECT (SELECT MIN(event_ts) FROM silver_crm_events WHERE is_campanha_lancamento_pix = 1 AND event_name = 'Notification Sent'), "
        "(SELECT COUNT(*) FROM gold_fct_resgate WHERE modalidade = 'PIX' AND substr(created_at, 1, 19) < "
        "(SELECT MIN(event_ts) FROM silver_crm_events WHERE is_campanha_lancamento_pix = 1 AND event_name = 'Notification Sent'))",
    "Operador: R$/ponto reportado x real":
        "SELECT mes, reais_por_ponto_relatorio, reais_por_ponto_real, pix_pontos_relatorio, pix_pontos_todos_status "
        "FROM gold_conciliacao_operador WHERE pix_pontos_relatorio IS NOT NULL ORDER BY mes",
    "Breakage: métricas candidatas":
        "SELECT metrica, valor FROM gold_breakage",
    "Passivo: saldo de pontos ao fim do período":
        "SELECT saldo_acumulado FROM gold_pontos_mensal ORDER BY mes DESC LIMIT 1",
}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", default=str(ROOT / "warehouse" / "pontua.db"))
    args = parser.parse_args()
    con = sqlite3.connect(args.db)
    for titulo, sql in CHECKS.items():
        rows = con.execute(sql).fetchall()
        print(f"\n## {titulo}")
        for r in rows:
            print("  ", r if len(r) > 1 else r[0])


if __name__ == "__main__":
    main()
