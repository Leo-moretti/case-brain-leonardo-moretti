-- grão: 1 linha por mês
-- base: pontos de itens APROVADO; percentuais sobre o total de pontos resgatados (Pix incluso)
-- variantes para as definições ainda não confirmadas com o negócio
DROP TABLE IF EXISTS gold_metas_mensal;
CREATE TABLE gold_metas_mensal AS
WITH m AS (
    SELECT
        mes,
        SUM(pontos_aprovados) AS pontos_total,
        SUM(CASE WHEN modalidade = 'AEREAS' THEN pontos_aprovados ELSE 0 END) AS pontos_aereas,
        SUM(CASE WHEN modalidade IN ('VAREJO_PRODUTO', 'TRANSFERENCIA_PARCEIRO') THEN pontos_aprovados ELSE 0 END) AS pontos_varejo,
        SUM(CASE WHEN modalidade = 'VAREJO_PRODUTO' THEN pontos_aprovados ELSE 0 END) AS pontos_varejo_produto,
        SUM(CASE WHEN modalidade = 'PIX' THEN pontos_aprovados ELSE 0 END) AS pontos_pix,
        SUM(pontos_aprovados_sem_lote) AS pontos_total_sem_lote,
        SUM(CASE WHEN modalidade = 'AEREAS' THEN pontos_aprovados_sem_lote ELSE 0 END) AS pontos_aereas_sem_lote
    FROM gold_resgates_mensal
    GROUP BY mes
)
SELECT
    mes,
    pontos_total,
    pontos_aereas,
    pontos_varejo,
    pontos_varejo_produto,
    pontos_pix,
    ROUND(100.0 * pontos_aereas / pontos_total, 2)          AS aereas_pct,
    ROUND(100.0 * pontos_varejo / pontos_total, 2)          AS varejo_pct,
    ROUND(100.0 * pontos_varejo_produto / pontos_total, 2)  AS varejo_produto_pct,
    ROUND(100.0 * pontos_pix / pontos_total, 2)             AS pix_pct,
    ROUND(100.0 * pontos_aereas / (pontos_total - pontos_pix), 2) AS aereas_pct_sem_pix,
    ROUND(100.0 * pontos_varejo / (pontos_total - pontos_pix), 2) AS varejo_pct_sem_pix,
    ROUND(100.0 * pontos_aereas_sem_lote / pontos_total_sem_lote, 2) AS aereas_pct_sem_lote,
    CASE WHEN 100.0 * pontos_aereas / pontos_total >= 50 THEN 1 ELSE 0 END AS atinge_meta_aereas,
    CASE WHEN 100.0 * pontos_varejo / pontos_total >= 20 THEN 1 ELSE 0 END AS atinge_meta_varejo
FROM m;
