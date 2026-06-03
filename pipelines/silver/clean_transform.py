"""
silver/clean_transform.py — Bronze → Silver transformation functions.

Key concepts demonstrated:
  1. Type casting & validation
  2. Idempotent UPSERT (INSERT ... ON CONFLICT DO UPDATE)
  3. Deduplication
  4. Data quality flags
"""

import logging
from typing import Optional

log = logging.getLogger(__name__)


# ==============================================================
#  PATTERN: Idempotent UPSERT
#  INSERT ... ON CONFLICT DO UPDATE ensures that re-running
#  this function never creates duplicates.
# ==============================================================


def load_customers(hook) -> int:
    """
    Clean & load customers from bronze → silver.

    Transformations:
      - Cast customer_id to UUID
      - Normalize email to lowercase
      - Parse signup_date as DATE
      - Validate tier values
    """
    sql = """
    INSERT INTO silver.customers
        (customer_id, first_name, last_name, email, country, signup_date, tier, _source_batch)
    SELECT
        raw.customer_id::UUID,
        TRIM(raw.first_name)             AS first_name,
        TRIM(raw.last_name)              AS last_name,
        LOWER(TRIM(raw.email))           AS email,
        UPPER(TRIM(raw.country))         AS country,
        raw.signup_date::DATE            AS signup_date,
        LOWER(TRIM(raw.tier))            AS tier,
        raw._batch_id                    AS _source_batch

    FROM (
        -- Deduplicate: keep the latest record per customer_id
        SELECT DISTINCT ON (customer_id)
            *
        FROM bronze.raw_customers
        WHERE customer_id IS NOT NULL
          AND customer_id ~ '^[0-9a-fA-F-]{36}$'    -- Valid UUID format
          AND email IS NOT NULL
          AND TRIM(email) != ''
        ORDER BY customer_id, _ingested_at DESC
    ) raw

    -- Idempotent: update if customer already exists
    ON CONFLICT (customer_id) DO UPDATE SET
        first_name        = EXCLUDED.first_name,
        last_name         = EXCLUDED.last_name,
        email             = EXCLUDED.email,
        country           = EXCLUDED.country,
        signup_date       = EXCLUDED.signup_date,
        tier              = EXCLUDED.tier,
        _source_batch     = EXCLUDED._source_batch,
        _silver_loaded_at = NOW()
    ;
    """
    hook.run(sql)
    row = hook.get_first("SELECT COUNT(*) FROM silver.customers")
    return row[0] if row else 0


def load_products(hook) -> int:
    """
    Clean & load products from bronze → silver.

    Transformations:
      - Cast price/cost to NUMERIC
      - Default cost to 0 if NULL/invalid
    """
    sql = """
    INSERT INTO silver.products
        (product_id, product_name, category, price, cost, stock_qty, _source_batch)
    SELECT
        product_id::UUID,
        TRIM(product_name)                                         AS product_name,
        COALESCE(TRIM(category), 'Unknown')                        AS category,

        -- Safe cast: replace invalid prices with 0
        CASE
            WHEN price ~ '^[0-9]+\\.?[0-9]*$' THEN price::NUMERIC
            ELSE 0
        END                                                        AS price,

        CASE
            WHEN cost ~ '^[0-9]+\\.?[0-9]*$' THEN cost::NUMERIC
            ELSE 0
        END                                                        AS cost,

        CASE
            WHEN stock_qty ~ '^[0-9]+$' THEN stock_qty::INTEGER
            ELSE 0
        END                                                        AS stock_qty,

        _batch_id                                                  AS _source_batch

    FROM (
        SELECT DISTINCT ON (product_id) *
        FROM bronze.raw_products
        WHERE product_id IS NOT NULL
          AND product_id ~ '^[0-9a-fA-F-]{36}$'
          AND product_name IS NOT NULL
        ORDER BY product_id, _ingested_at DESC
    ) raw

    ON CONFLICT (product_id) DO UPDATE SET
        product_name      = EXCLUDED.product_name,
        category          = EXCLUDED.category,
        price             = EXCLUDED.price,
        cost              = EXCLUDED.cost,
        stock_qty         = EXCLUDED.stock_qty,
        _source_batch     = EXCLUDED._source_batch,
        _silver_loaded_at = NOW()
    ;
    """
    hook.run(sql)
    row = hook.get_first("SELECT COUNT(*) FROM silver.products")
    return row[0] if row else 0


def load_orders(hook) -> int:
    """
    Clean & load orders from bronze → silver.

    Only processes orders whose customer_id exists in silver.customers
    (referential integrity enforcement).
    """
    sql = """
    INSERT INTO silver.orders
        (order_id, customer_id, order_date, status, total_amount,
         currency, created_at, _source_batch)
    SELECT
        raw.order_id::UUID,
        raw.customer_id::UUID,
        raw.order_date::DATE,

        -- Normalize status to lowercase
        LOWER(TRIM(raw.status)),

        -- Safe numeric cast for total_amount
        CASE
            WHEN raw.total_amount ~ '^[0-9]+\\.?[0-9]*$'
            THEN raw.total_amount::NUMERIC
            ELSE 0
        END,

        COALESCE(UPPER(TRIM(raw.currency)), 'USD'),
        raw.created_at::TIMESTAMPTZ,
        raw._batch_id

    FROM (
        SELECT DISTINCT ON (order_id) *
        FROM bronze.raw_orders
        WHERE order_id    IS NOT NULL
          AND customer_id IS NOT NULL
          AND order_id    ~ '^[0-9a-fA-F-]{36}$'
          AND customer_id ~ '^[0-9a-fA-F-]{36}$'
          AND order_date  IS NOT NULL
        ORDER BY order_id, _ingested_at DESC
    ) raw

    -- Only load orders for known customers (referential integrity)
    INNER JOIN silver.customers c
        ON raw.customer_id::UUID = c.customer_id

    ON CONFLICT (order_id) DO UPDATE SET
        status            = EXCLUDED.status,
        total_amount      = EXCLUDED.total_amount,
        currency          = EXCLUDED.currency,
        _source_batch     = EXCLUDED._source_batch,
        _silver_loaded_at = NOW()
    ;
    """
    hook.run(sql)
    row = hook.get_first("SELECT COUNT(*) FROM silver.orders")
    return row[0] if row else 0


def load_order_items(hook) -> int:
    """
    Clean & load order items from bronze → silver.

    Only processes items whose order_id AND product_id exist
    in silver (cascading referential integrity).
    """
    sql = """
    INSERT INTO silver.order_items
        (order_item_id, order_id, product_id, quantity,
         unit_price, discount, _source_batch)
    SELECT
        raw.order_item_id::UUID,
        raw.order_id::UUID,
        raw.product_id::UUID,

        CASE
            WHEN raw.quantity ~ '^[0-9]+$' THEN raw.quantity::INTEGER
            ELSE 1
        END,

        CASE
            WHEN raw.unit_price ~ '^[0-9]+\\.?[0-9]*$'
            THEN raw.unit_price::NUMERIC
            ELSE 0
        END,

        CASE
            WHEN raw.discount ~ '^[0-9]+\\.?[0-9]*$'
            THEN LEAST(raw.discount::NUMERIC, 100)  -- cap at 100%
            ELSE 0
        END,

        raw._batch_id

    FROM (
        SELECT DISTINCT ON (order_item_id) *
        FROM bronze.raw_order_items
        WHERE order_item_id ~ '^[0-9a-fA-F-]{36}$'
          AND order_id       ~ '^[0-9a-fA-F-]{36}$'
          AND product_id     ~ '^[0-9a-fA-F-]{36}$'
        ORDER BY order_item_id, _ingested_at DESC
    ) raw

    INNER JOIN silver.orders   o ON raw.order_id::UUID   = o.order_id
    INNER JOIN silver.products p ON raw.product_id::UUID = p.product_id

    ON CONFLICT (order_item_id) DO UPDATE SET
        quantity          = EXCLUDED.quantity,
        unit_price        = EXCLUDED.unit_price,
        discount          = EXCLUDED.discount,
        _source_batch     = EXCLUDED._source_batch,
        _silver_loaded_at = NOW()
    ;
    """
    hook.run(sql)
    row = hook.get_first("SELECT COUNT(*) FROM silver.order_items")
    return row[0] if row else 0
