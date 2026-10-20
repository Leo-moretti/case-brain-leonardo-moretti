-- grão: 1 linha por pedido (order_id)
-- orders.user_id vem 100% vazio na origem; o usuário é resolvido via carts (1:1 por cart_id)
DROP TABLE IF EXISTS silver_orders;
CREATE TABLE silver_orders AS
SELECT
    o.order_id,
    o.cart_id,
    c.user_id,
    c.channel,
    o.created_at,
    substr(o.created_at, 1, 10) AS created_date,
    substr(o.created_at, 1, 7)  AS created_month,
    o.status,
    o.status_updated_at
FROM bronze_orders o
LEFT JOIN bronze_carts c ON c.cart_id = o.cart_id;
