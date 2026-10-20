-- grão: 1 linha por métrica candidata de breakage (nenhuma é a "oficial"; ver descricao)
DROP TABLE IF EXISTS gold_breakage;
CREATE TABLE gold_breakage AS
WITH t AS (
    SELECT
        SUM(CASE WHEN operation_code = 100 THEN points ELSE 0 END)        AS migrados,
        SUM(CASE WHEN operation_code = 1   THEN points ELSE 0 END)        AS creditados,
        -SUM(CASE WHEN operation_code IN (3, 103) THEN points ELSE 0 END) AS expirados,
        -SUM(CASE WHEN operation_code = 3  THEN points ELSE 0 END)        AS expirados_programa_novo,
        -SUM(CASE WHEN operation_code = 2  THEN points ELSE 0 END)        AS resgatados,
        -SUM(CASE WHEN operation_code IN (3, 103) AND movement_month BETWEEN '2026-02' AND '2026-05' THEN points ELSE 0 END) AS expirados_fev_mai,
        -SUM(CASE WHEN operation_code = 2 AND movement_month BETWEEN '2026-02' AND '2026-05' THEN points ELSE 0 END)          AS resgatados_fev_mai,
        (SELECT MIN(valid_until) FROM silver_points_ledger WHERE operation_code = 1) AS primeiro_vencimento_programa_novo
    FROM silver_points_ledger
)
SELECT 'expirado_sobre_migrado_pct' AS metrica, ROUND(100.0 * expirados / migrados, 2) AS valor,
       'Pontos expirados / pontos migrados do programa anterior. Única expiração existente é de migração.' AS descricao FROM t
UNION ALL
SELECT 'expirado_sobre_expirado_mais_resgatado_pct', ROUND(100.0 * expirados / (expirados + resgatados), 2),
       'Dos pontos que saíram do saldo, quanto saiu por expiração.' FROM t
UNION ALL
SELECT 'expirado_sobre_resgatado_fev_mai_pct', ROUND(100.0 * expirados_fev_mai / resgatados_fev_mai, 2),
       'Razão expirado/resgatado em fev-mai/26. Não é breakage; provável origem do número de 40%.' FROM t
UNION ALL
SELECT 'expirados_programa_novo_pontos', expirados_programa_novo,
       'Pontos do programa novo (código 3) já expirados. Zero: nenhum crédito venceu ainda.' FROM t
UNION ALL
SELECT 'primeiro_vencimento_programa_novo', primeiro_vencimento_programa_novo,
       'Data do primeiro vencimento de crédito do programa novo; antes disso breakage real não é mensurável.' FROM t;
