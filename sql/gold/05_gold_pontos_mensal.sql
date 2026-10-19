-- grão: 1 linha por mês de movimento do ledger
DROP TABLE IF EXISTS gold_pontos_mensal;
CREATE TABLE gold_pontos_mensal AS
WITH m AS (
    SELECT
        movement_month AS mes,
        SUM(CASE WHEN operation_code = 1   THEN points ELSE 0 END)  AS pontos_creditados,
        SUM(CASE WHEN operation_code = 100 THEN points ELSE 0 END)  AS pontos_migrados,
        -SUM(CASE WHEN operation_code = 2  THEN points ELSE 0 END)  AS pontos_resgatados,
        SUM(CASE WHEN operation_code = 14  THEN points ELSE 0 END)  AS pontos_estornados,
        -SUM(CASE WHEN operation_code IN (3, 103) THEN points ELSE 0 END) AS pontos_expirados,
        SUM(points) AS variacao_saldo
    FROM silver_points_ledger
    GROUP BY movement_month
)
SELECT
    m.*,
    SUM(variacao_saldo) OVER (ORDER BY mes) AS saldo_acumulado
FROM m;
