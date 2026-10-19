-- grão: 1 linha por grupo de exposição à campanha de lançamento do Pix
-- adoção = usuário com ao menos 1 resgate Pix APROVADO ou ESTORNADO
DROP TABLE IF EXISTS gold_campanha_pix;
CREATE TABLE gold_campanha_pix AS
WITH exp AS (
    SELECT
        user_id,
        MAX(CASE WHEN event_name = 'Notification Sent' THEN 1 ELSE 0 END) AS recebeu,
        MAX(CASE WHEN event_name IN ('Notification Viewed', 'Notification Clicked') THEN 1 ELSE 0 END) AS abriu,
        MIN(CASE WHEN event_name = 'Notification Sent' THEN event_ts END) AS primeiro_envio
    FROM silver_crm_events
    WHERE is_campanha_lancamento_pix = 1
    GROUP BY user_id
),
pix AS (
    SELECT user_id, MIN(created_at) AS primeiro_pix
    FROM gold_fct_resgate
    WHERE modalidade = 'PIX' AND status IN ('APROVADO', 'ESTORNADO')
    GROUP BY user_id
),
base AS (
    SELECT
        u.user_id,
        CASE
            WHEN COALESCE(e.recebeu, 0) = 0 THEN '1_nao_recebeu'
            WHEN e.abriu = 1               THEN '3_recebeu_e_abriu'
            ELSE                                '2_recebeu_nao_abriu'
        END AS grupo,
        u.resgatou_antes_pix,
        p.primeiro_pix,
        CASE WHEN p.primeiro_pix IS NOT NULL AND e.primeiro_envio IS NOT NULL
              AND substr(p.primeiro_pix, 1, 19) < e.primeiro_envio THEN 1 ELSE 0 END AS pix_antes_do_email
    FROM gold_dim_usuario u
    LEFT JOIN exp e USING (user_id)
    LEFT JOIN pix p USING (user_id)
)
SELECT
    grupo,
    COUNT(*)                                         AS usuarios,
    SUM(CASE WHEN primeiro_pix IS NOT NULL THEN 1 ELSE 0 END) AS usuarios_pix,
    ROUND(100.0 * SUM(CASE WHEN primeiro_pix IS NOT NULL THEN 1 ELSE 0 END) / COUNT(*), 2) AS adocao_pix_pct,
    ROUND(100.0 * SUM(resgatou_antes_pix) / COUNT(*), 2) AS resgatadores_previos_pct,
    SUM(pix_antes_do_email) AS usuarios_pix_antes_do_email
FROM base
GROUP BY grupo;
