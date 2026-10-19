-- grão: 1 linha por mês do relatório do operador ao banco
DROP TABLE IF EXISTS silver_relatorio_operador;
CREATE TABLE silver_relatorio_operador AS
SELECT
    mes,
    CAST(aereas_pct AS REAL)                AS aereas_pct,
    CAST(varejo_pct AS REAL)                AS varejo_pct,
    CAST(pix_pct AS REAL)                   AS pix_pct,
    CAST(pix_reais AS REAL)                 AS pix_reais,
    CAST(CAST(pix_pontos AS REAL) AS INTEGER)     AS pix_pontos,
    CAST(CAST(pix_transacoes AS REAL) AS INTEGER) AS pix_transacoes,
    CAST(emails_enviados AS INTEGER)        AS emails_enviados,
    CAST(CAST(push_enviados AS REAL) AS INTEGER)  AS push_enviados
FROM bronze_relatorio_mensal_cliente;
