-- grão: 1 linha por mês x modalidade de resgate
DROP TABLE IF EXISTS gold_resgates_mensal;
CREATE TABLE gold_resgates_mensal AS
SELECT
    mes,
    modalidade,
    COUNT(*)                                                         AS itens_total,
    SUM(is_aprovado)                                                 AS itens_aprovados,
    SUM(CASE WHEN status IN ('CANCELADO', 'INVALIDO') THEN 1 ELSE 0 END) AS itens_cancelados_invalidos,
    SUM(CASE WHEN status = 'ESTORNADO' THEN 1 ELSE 0 END)           AS itens_estornados,
    SUM(CASE WHEN is_aprovado = 1 THEN pontos ELSE 0 END)            AS pontos_aprovados,
    SUM(CASE WHEN is_aprovado = 1 AND flag_lote_20260112 = 0 THEN pontos ELSE 0 END) AS pontos_aprovados_sem_lote,
    SUM(CASE WHEN status = 'ESTORNADO' THEN pontos ELSE 0 END)       AS pontos_estornados,
    COUNT(DISTINCT CASE WHEN is_aprovado = 1 THEN user_id END)       AS usuarios_aprovados,
    ROUND(SUM(CASE WHEN is_aprovado = 1 THEN valor_produto_reais ELSE 0 END), 2) AS valor_produto_reais,
    ROUND(SUM(CASE WHEN is_aprovado = 1 THEN copagamento_reais ELSE 0 END), 2)   AS copagamento_reais,
    ROUND(SUM(CASE WHEN is_aprovado = 1 THEN custo_pontos_reais ELSE 0 END), 2)  AS custo_pontos_reais,
    ROUND(SUM(CASE WHEN is_aprovado = 1 THEN custo_pontos_reais ELSE 0 END)
          / NULLIF(SUM(CASE WHEN is_aprovado = 1 THEN pontos ELSE 0 END), 0), 5) AS custo_por_ponto_reais
FROM gold_fct_resgate
GROUP BY mes, modalidade;
