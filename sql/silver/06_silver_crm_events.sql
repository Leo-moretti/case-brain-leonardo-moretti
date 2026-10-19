-- grão: 1 linha por evento do CRM (sem chave natural; _row_id da bronze)
-- 20.252 eventos sem user_id: recuperados via device_id (device -> user é 1:1 nos dados)
-- event_ts vem sem fuso; tratado como horário local (hipótese documentada)
DROP TABLE IF EXISTS silver_crm_events;
CREATE TABLE silver_crm_events AS
WITH device_user AS (
    SELECT device_id, MIN(user_id) AS user_id
    FROM bronze_crm_events
    WHERE user_id IS NOT NULL
    GROUP BY device_id
)
SELECT
    e._row_id AS crm_event_id,
    e.event_ts,
    substr(e.event_ts, 1, 10) AS event_date,
    substr(e.event_ts, 1, 7)  AS event_month,
    COALESCE(e.user_id, d.user_id) AS user_id,
    CASE WHEN e.user_id IS NULL THEN 1 ELSE 0 END AS user_id_from_device,
    e.device_id,
    e.event_name,
    e.campaign_type,
    CASE
        WHEN e.campaign_type = 'Email'                  THEN 'EMAIL'
        WHEN e.campaign_type LIKE 'Mobile Push%'
          OR e.campaign_type = 'Push'                   THEN 'PUSH'
        WHEN e.campaign_type = 'Facebook Audiences'     THEN 'FACEBOOK'
    END AS canal,
    e.campaign_id,
    CASE WHEN e.campaign_id LIKE 'CMP_LANCAMENTO_PIX%' THEN 1 ELSE 0 END AS is_campanha_lancamento_pix,
    e.control_group,
    json_extract(e.event_properties, '$.link')   AS link,
    json_extract(e.event_properties, '$.reason') AS failure_reason
FROM bronze_crm_events e
LEFT JOIN device_user d ON d.device_id = e.device_id;
