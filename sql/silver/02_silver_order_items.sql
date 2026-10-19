-- grão: 1 linha por item de pedido (order_item_id)
-- modalidade separa o que category_macro mistura:
--   Cashback = Pix (resgate) + COMPRA_PONTOS (venda de pontos, não é resgate)
--   Varejo   = produtos + transferências para programas parceiros
DROP TABLE IF EXISTS silver_order_items;
CREATE TABLE silver_order_items AS
SELECT
    i.order_item_id,
    i.order_id,
    o.user_id,
    o.channel,
    i.created_at,
    substr(i.created_at, 1, 10) AS created_date,
    substr(i.created_at, 1, 7)  AS created_month,
    i.status,
    o.status AS order_status,
    i.product_type,
    i.supplier_name,
    i.supplier_responsible,
    i.category_macro,
    CASE
        WHEN i.product_type = 'COMPRA_PONTOS'                                  THEN 'COMPRA_PONTOS'
        WHEN i.supplier_name = 'Pix Pontua+'                                   THEN 'PIX'
        WHEN i.category_macro = 'Aereas'                                       THEN 'AEREAS'
        WHEN i.category_macro = 'Varejo' AND i.product_type = 'TRANSFERENCIA'  THEN 'TRANSFERENCIA_PARCEIRO'
        WHEN i.category_macro = 'Varejo'                                       THEN 'VAREJO_PRODUTO'
        ELSE 'OUTRO'
    END AS modalidade,
    CAST(i.paid_points AS INTEGER)      AS paid_points,
    CAST(i.paid_currency AS REAL)       AS paid_currency,
    CAST(i.product_value AS REAL)       AS product_value,
    CAST(i.refunded_points AS INTEGER)  AS refunded_points,
    CAST(i.quantity AS INTEGER)         AS quantity,
    CASE WHEN i.product_type <> 'COMPRA_PONTOS' THEN 1 ELSE 0 END AS is_resgate,
    CASE WHEN i.status = 'APROVADO' THEN 1 ELSE 0 END             AS is_aprovado,
    -- lote atípico: 1.520 resgates de aéreas em 12/01/2026, 99,7% de usuários migrados
    CASE WHEN i.category_macro = 'Aereas' AND substr(i.created_at, 1, 10) = '2026-01-12'
         THEN 1 ELSE 0 END AS flag_lote_20260112
FROM bronze_order_items i
LEFT JOIN silver_orders o ON o.order_id = i.order_id;
