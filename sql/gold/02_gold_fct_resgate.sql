-- grão: 1 linha por item de resgate (order_item_id), todos os status; exclui COMPRA_PONTOS
DROP TABLE IF EXISTS gold_fct_resgate;
CREATE TABLE gold_fct_resgate AS
SELECT
    i.order_item_id,
    i.order_id,
    i.user_id,
    u.card_class_atual,
    i.channel,
    i.created_at,
    i.created_date,
    i.created_month AS mes,
    CASE WHEN i.created_at >= '2026-05-27' THEN 'POS_PIX' ELSE 'PRE_PIX' END AS periodo_pix,
    i.status,
    i.modalidade,
    i.category_macro,
    i.product_type,
    i.supplier_name,
    i.supplier_responsible,
    i.paid_points  AS pontos,
    i.paid_currency AS copagamento_reais,
    i.product_value AS valor_produto_reais,
    i.product_value - i.paid_currency AS custo_pontos_reais,
    i.refunded_points AS pontos_estornados_parcial,
    i.is_aprovado,
    i.flag_lote_20260112
FROM silver_order_items i
LEFT JOIN gold_dim_usuario u USING (user_id)
WHERE i.is_resgate = 1;
