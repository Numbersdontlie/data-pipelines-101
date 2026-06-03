/* ============================================================
   SQLMesh Model: silver__customers
   Layer:         Silver
   Type:          FULL (full refresh)

   Demonstrates: type casting, deduplication, computed columns
   ============================================================ */

MODEL (
    name silver.customers_sqlmesh,
    kind FULL,
    grain (customer_id),
    description 'Cleaned and typed customers from bronze layer'
);

SELECT
    customer_id::UUID                               AS customer_id,
    TRIM(first_name)                                AS first_name,
    TRIM(last_name)                                 AS last_name,
    TRIM(first_name) || ' ' || TRIM(last_name)      AS full_name,
    LOWER(TRIM(email))                              AS email,
    UPPER(TRIM(country))                            AS country,
    signup_date::DATE                               AS signup_date,
    LOWER(TRIM(tier))                               AS tier,
    _batch_id                                       AS source_batch,
    NOW()                                           AS silver_loaded_at

FROM (
    -- Deduplicate: latest record per customer_id wins
    SELECT DISTINCT ON (customer_id)
        *
    FROM bronze.raw_customers
    WHERE customer_id IS NOT NULL
      AND customer_id ~ '^[0-9a-fA-F-]{36}$'
      AND email IS NOT NULL
      AND TRIM(email) <> ''
    ORDER BY customer_id, _ingested_at DESC
) deduped
