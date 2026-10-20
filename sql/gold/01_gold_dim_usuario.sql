-- grão: 1 linha por usuário (user_id) presente em cards
DROP TABLE IF EXISTS gold_dim_usuario;
CREATE TABLE gold_dim_usuario AS
WITH atual AS (
    SELECT user_id, card_class, card_class_rank, card_flag
    FROM silver_cards WHERE is_most_recent = 1
),
contas AS (
    SELECT user_id, COUNT(*) AS qtd_contas FROM silver_cards GROUP BY user_id
),
mig AS (
    SELECT DISTINCT user_id FROM silver_points_ledger WHERE operation_code = 100
),
res AS (
    SELECT user_id,
           MIN(created_at) AS primeiro_resgate_em,
           MIN(CASE WHEN modalidade = 'PIX' THEN created_at END) AS primeiro_pix_em,
           MAX(CASE WHEN created_at < '2026-05-27' THEN 1 ELSE 0 END) AS resgatou_antes_pix
    FROM silver_order_items
    WHERE is_resgate = 1 AND status = 'APROVADO'
    GROUP BY user_id
)
SELECT
    a.user_id,
    a.card_class AS card_class_atual,
    a.card_class_rank,
    a.card_flag AS card_flag_atual,
    c.qtd_contas,
    CASE WHEN m.user_id IS NOT NULL THEN 1 ELSE 0 END AS tem_saldo_migrado,
    r.primeiro_resgate_em,
    r.primeiro_pix_em,
    CASE WHEN r.primeiro_pix_em IS NOT NULL THEN 1 ELSE 0 END AS usou_pix,
    COALESCE(r.resgatou_antes_pix, 0) AS resgatou_antes_pix
FROM atual a
JOIN contas c USING (user_id)
LEFT JOIN mig m USING (user_id)
LEFT JOIN res r USING (user_id);
