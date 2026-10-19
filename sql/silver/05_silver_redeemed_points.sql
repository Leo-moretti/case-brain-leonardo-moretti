-- grão: 1 linha por movimento de pontos de um item numa conta (sem chave natural; _row_id da bronze)
-- RESERVA + CANCELADO_RESERVA se anulam; um item pode ter 2 RESGATE (pagamento dividido entre contas)
DROP TABLE IF EXISTS silver_redeemed_points;
CREATE TABLE silver_redeemed_points AS
SELECT
    _row_id AS redeemed_row_id,
    order_item_id,
    account_id,
    movement_type,
    CAST(points AS INTEGER) AS points
FROM bronze_redeemed_points;
