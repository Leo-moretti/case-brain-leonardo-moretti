-- grão: 1 linha por movimento de pontos (movement_id); points já vem com sinal
DROP TABLE IF EXISTS silver_points_ledger;
CREATE TABLE silver_points_ledger AS
SELECT
    l.movement_id,
    l.user_id,
    l.account_id,
    CAST(l.operation_code AS INTEGER) AS operation_code,
    d.operation_name,
    d.direction,
    CAST(CAST(l.points AS REAL) AS INTEGER) AS points,
    l.movement_at,
    substr(l.movement_at, 1, 10) AS movement_date,
    substr(l.movement_at, 1, 7)  AS movement_month,
    l.valid_until,
    CASE WHEN CAST(l.operation_code AS INTEGER) IN (100, 103) THEN 1 ELSE 0 END AS is_migracao
FROM bronze_points_ledger l
LEFT JOIN bronze_dim_operation d ON d.operation_code = l.operation_code;
