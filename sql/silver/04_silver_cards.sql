-- grão: 1 linha por conta/cartão (account_id)
DROP TABLE IF EXISTS silver_cards;
CREATE TABLE silver_cards AS
SELECT
    account_id,
    user_id,
    card_class,
    CASE card_class
        WHEN 'Essencial'    THEN 1
        WHEN 'Gold'         THEN 2
        WHEN 'Platinum'     THEN 3
        WHEN 'Platinum Elo' THEN 4
        WHEN 'Infinite'     THEN 5
        WHEN 'Black'        THEN 6
    END AS card_class_rank,
    card_flag,
    created_at,
    CASE WHEN is_most_recent = 'True' THEN 1 ELSE 0 END AS is_most_recent
FROM bronze_cards;
