-- grão: 1 linha por mês do relatório do operador; compara o reportado com o recalculado
DROP TABLE IF EXISTS gold_conciliacao_operador;
CREATE TABLE gold_conciliacao_operador AS
WITH pix AS (
    SELECT
        mes,
        COUNT(*)                                         AS pix_transacoes_todos_status,
        SUM(is_aprovado)                                 AS pix_transacoes_aprovadas,
        SUM(pontos)                                      AS pix_pontos_todos_status,
        SUM(CASE WHEN is_aprovado = 1 THEN pontos END)   AS pix_pontos_aprovados,
        ROUND(SUM(CASE WHEN is_aprovado = 1 THEN valor_produto_reais END), 2) AS pix_reais_aprovados
    FROM gold_fct_resgate
    WHERE modalidade = 'PIX'
    GROUP BY mes
),
crm AS (
    SELECT
        event_month AS mes,
        SUM(CASE WHEN event_name = 'Notification Sent' AND canal = 'EMAIL' THEN 1 ELSE 0 END) AS emails_crm,
        SUM(CASE WHEN event_name = 'Notification Sent' AND campaign_type LIKE 'Mobile Push%' THEN 1 ELSE 0 END) AS push_crm
    FROM silver_crm_events
    GROUP BY event_month
)
SELECT
    r.mes,
    r.aereas_pct  AS aereas_pct_relatorio,
    g.aereas_pct  AS aereas_pct_calculado,
    r.varejo_pct  AS varejo_pct_relatorio,
    g.varejo_pct  AS varejo_pct_calculado,
    r.pix_pct     AS pix_pct_relatorio,
    g.pix_pct     AS pix_pct_calculado,
    r.pix_transacoes AS pix_transacoes_relatorio,
    p.pix_transacoes_todos_status,
    p.pix_transacoes_aprovadas,
    r.pix_pontos  AS pix_pontos_relatorio,
    p.pix_pontos_todos_status,
    p.pix_pontos_aprovados,
    r.pix_reais   AS pix_reais_relatorio,
    p.pix_reais_aprovados,
    ROUND(r.pix_reais / r.pix_pontos, 5)                     AS reais_por_ponto_relatorio,
    ROUND(p.pix_reais_aprovados / p.pix_pontos_aprovados, 5) AS reais_por_ponto_real,
    r.emails_enviados AS emails_relatorio,
    c.emails_crm,
    r.push_enviados   AS push_relatorio,
    c.push_crm
FROM silver_relatorio_operador r
LEFT JOIN gold_metas_mensal g ON g.mes = r.mes
LEFT JOIN pix p ON p.mes = r.mes
LEFT JOIN crm c ON c.mes = r.mes;
