"""
idempotency/patterns.py — Idempotent pipeline patterns explained.

DEFINITION:
  A pipeline is idempotent if running it N times produces
  the same result as running it once.

WHY IT MATTERS:
  - Airflow retries failed tasks
  - Pipelines may be re-run to fix data quality issues
  - Backfills require replaying historical loads
  - Cloud infra can restart containers mid-run

This module shows 4 common patterns with PostgreSQL examples.
"""

from datetime import date


# ==============================================================
#  PATTERN 1: TRUNCATE + INSERT (Full Refresh)
#  Best for: Small tables, Gold aggregations, reference data
#  Pros: Simple, always correct
#  Cons: Downtime window between truncate & insert
# ==============================================================

PATTERN_1_TRUNCATE_INSERT = """
-- Pattern 1: TRUNCATE + INSERT inside a transaction
-- The transaction means no reader ever sees an empty table.

BEGIN;

TRUNCATE TABLE gold.daily_revenue;

INSERT INTO gold.daily_revenue (revenue_date, order_count, gross_revenue)
SELECT
    order_date,
    COUNT(*),
    SUM(total_amount)
FROM silver.orders
WHERE status = 'completed'
GROUP BY order_date;

COMMIT;

-- ✅ Run this 10 times → same result every time
"""


# ==============================================================
#  PATTERN 2: INSERT ... ON CONFLICT DO UPDATE (UPSERT)
#  Best for: Silver layer, slowly-changing dimensions
#  Pros: No truncation, handles new + updated rows
#  Cons: Requires a PRIMARY KEY or UNIQUE constraint
# ==============================================================

PATTERN_2_UPSERT = """
-- Pattern 2: Idempotent UPSERT
-- Requires: UNIQUE constraint or PRIMARY KEY on target

INSERT INTO silver.customers
    (customer_id, first_name, last_name, email, tier)
SELECT
    customer_id::UUID,
    first_name,
    last_name,
    LOWER(email),
    tier
FROM bronze.raw_customers
WHERE customer_id IS NOT NULL

ON CONFLICT (customer_id)       -- if the PK already exists...
DO UPDATE SET                   -- ...update instead of error
    first_name = EXCLUDED.first_name,
    last_name  = EXCLUDED.last_name,
    email      = EXCLUDED.email,
    tier       = EXCLUDED.tier,
    _silver_loaded_at = NOW();  -- track when it was last updated

-- ✅ Run this 10 times → same result, no duplicates
"""


# ==============================================================
#  PATTERN 3: DELETE + INSERT (Partition / Date-based)
#  Best for: Incremental loads by date partition
#  Pros: Predictable, works without PK
#  Cons: Need to know the partition key (e.g. load_date)
# ==============================================================

PATTERN_3_DELETE_INSERT = """
-- Pattern 3: Delete the partition window, then re-insert
-- Use when you're processing a specific date range

-- Step 1: Remove the partition we're about to reload
DELETE FROM gold.daily_revenue
WHERE revenue_date = :load_date;   -- parameterized!

-- Step 2: Insert fresh data for that partition
INSERT INTO gold.daily_revenue (revenue_date, order_count, gross_revenue)
SELECT
    order_date,
    COUNT(*),
    SUM(total_amount)
FROM silver.orders
WHERE order_date = :load_date
GROUP BY order_date;

-- ✅ Re-running for the same :load_date → same result
-- ✅ Safe to backfill multiple dates in sequence
"""


# ==============================================================
#  PATTERN 4: Watermark / Incremental
#  Best for: Very large Bronze tables, streaming-style loads
#  Pros: Only processes new rows → fast
#  Cons: Need a reliable watermark column (_ingested_at, updated_at)
# ==============================================================

PATTERN_4_WATERMARK = """
-- Pattern 4: Watermark-based incremental load
-- Track the last processed timestamp and only load new rows

-- Step 1: Get last watermark
SELECT COALESCE(MAX(finished_at), '1970-01-01'::TIMESTAMPTZ)
FROM bronze.pipeline_runs
WHERE pipeline_name = 'bronze_orders'
  AND status = 'SUCCESS';

-- Step 2: Load only rows after the watermark
INSERT INTO silver.orders (order_id, customer_id, order_date, ...)
SELECT order_id::UUID, customer_id::UUID, order_date::DATE, ...
FROM bronze.raw_orders
WHERE _ingested_at > :last_watermark     -- only new rows
ON CONFLICT (order_id) DO UPDATE SET ... -- handle late-arriving updates

-- Step 3: Update watermark
INSERT INTO bronze.pipeline_runs (pipeline_name, layer, status, finished_at)
VALUES ('bronze_orders', 'silver', 'SUCCESS', NOW());

-- ✅ Each run only touches new data → scalable
-- ⚠️  Watch out for late-arriving data! Use a safety buffer:
--     WHERE _ingested_at > :last_watermark - INTERVAL '1 hour'
"""


# ==============================================================
#  COMPARISON TABLE
# ==============================================================

IDEMPOTENCY_PATTERNS = {
    "truncate_insert": {
        "name": "TRUNCATE + INSERT",
        "best_for": "Gold aggregations, small tables, reference data",
        "idempotent": True,
        "handles_updates": True,
        "handles_deletes": True,
        "performance": "O(total rows)",
        "complexity": "Low",
        "sql": PATTERN_1_TRUNCATE_INSERT,
    },
    "upsert": {
        "name": "INSERT ... ON CONFLICT",
        "best_for": "Silver layer, dimensions with natural keys",
        "idempotent": True,
        "handles_updates": True,
        "handles_deletes": False,
        "performance": "O(new/changed rows)",
        "complexity": "Medium",
        "sql": PATTERN_2_UPSERT,
    },
    "delete_insert": {
        "name": "DELETE + INSERT (partition)",
        "best_for": "Date-partitioned incremental loads",
        "idempotent": True,
        "handles_updates": True,
        "handles_deletes": True,
        "performance": "O(partition size)",
        "complexity": "Medium",
        "sql": PATTERN_3_DELETE_INSERT,
    },
    "watermark": {
        "name": "Watermark Incremental",
        "best_for": "Large Bronze tables, high-frequency loads",
        "idempotent": "Partial (need UPSERT at destination)",
        "handles_updates": "If watermark column is updated_at",
        "handles_deletes": False,
        "performance": "O(new rows only) — fastest",
        "complexity": "High",
        "sql": PATTERN_4_WATERMARK,
    },
}


def print_pattern_guide():
    """Print a formatted guide to idempotency patterns."""
    print("\n" + "=" * 60)
    print("  IDEMPOTENCY PATTERNS — Data Engineering Playground")
    print("=" * 60)
    for key, p in IDEMPOTENCY_PATTERNS.items():
        print(f"\n{'─' * 40}")
        print(f"  Pattern  : {p['name']}")
        print(f"  Best for : {p['best_for']}")
        print(f"  Perf     : {p['performance']}")
        print(f"  Deletes? : {p['handles_deletes']}")
        print(f"  Complex  : {p['complexity']}")
    print()


if __name__ == "__main__":
    print_pattern_guide()
