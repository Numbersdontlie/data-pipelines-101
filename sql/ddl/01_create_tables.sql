-- ================================================================
--  DDL Module — Data Engineering Playground
--  File: sql/ddl/01_create_tables.sql
--  Topic: Table design for analytics workloads
-- ================================================================

-- ─── Key Concepts ───────────────────────────────────────────────
-- 1. Choose the right data types (don't store numbers as TEXT)
-- 2. Use constraints to enforce data quality at the DataBase level
-- 3. Generated columns for derived values
-- 4. Indexes on frequently-filtered columns

-- ─── Example: Well-designed analytics table ─────────────────────

CREATE TABLE IF NOT EXISTS example.sales (
    -- Surrogate key (auto-increment, never reused)
    sale_id          BIGSERIAL PRIMARY KEY,

    -- Business keys (natural, from source system)
    order_id         UUID NOT NULL,
    customer_id      UUID NOT NULL,
    product_id       UUID NOT NULL,

    -- Dimensions
    sale_date        DATE NOT NULL,
    region           TEXT NOT NULL,
    channel          TEXT CHECK (channel IN ('web', 'mobile', 'retail', 'b2b')),

    -- Measures (always NUMERIC for money, never FLOAT)
    quantity         INTEGER NOT NULL CHECK (quantity > 0),
    unit_price       NUMERIC(10, 2) NOT NULL CHECK (unit_price >= 0),
    discount_pct     NUMERIC(5, 2) NOT NULL DEFAULT 0
                         CHECK (discount_pct BETWEEN 0 AND 100),

    -- Computed column (auto-maintained by DB)
    line_total       NUMERIC(14, 2) GENERATED ALWAYS AS (
                         quantity * unit_price * (1 - discount_pct / 100)
                     ) STORED,

    -- Audit columns (every analytics table should have these)
    created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    _batch_id        TEXT,
    _source          TEXT
);

-- ─── Indexes ────────────────────────────────────────────────────
-- Index on date for time-series queries
CREATE INDEX IF NOT EXISTS idx_sales_date
    ON example.sales(sale_date);

-- Composite index for common filter patterns
CREATE INDEX IF NOT EXISTS idx_sales_date_region
    ON example.sales(sale_date, region);

-- Index for customer lookups
CREATE INDEX IF NOT EXISTS idx_sales_customer
    ON example.sales(customer_id);

-- ─── Partitioning (advanced) ─────────────────────────────────────
-- For very large tables, partition by date

CREATE TABLE IF NOT EXISTS example.sales_partitioned (
    LIKE example.sales INCLUDING ALL
) PARTITION BY RANGE (sale_date);

-- Create monthly partitions
CREATE TABLE IF NOT EXISTS example.sales_2024_01
    PARTITION OF example.sales_partitioned
    FOR VALUES FROM ('2024-01-01') TO ('2024-02-01');

CREATE TABLE IF NOT EXISTS example.sales_2024_02
    PARTITION OF example.sales_partitioned
    FOR VALUES FROM ('2024-02-01') TO ('2024-03-01');

-- ─── ❌ Common Anti-Patterns ─────────────────────────────────────

/*
-- ❌ DON'T: Store numbers as TEXT
CREATE TABLE bad_sales (
    price TEXT,           -- Should be NUMERIC
    quantity TEXT,        -- Should be INTEGER
    sale_date TEXT        -- Should be DATE
);

-- ❌ DON'T: No constraints
CREATE TABLE bad_orders (
    amount NUMERIC        -- What if someone inserts -9999?
);

-- ❌ DON'T: Missing audit columns
CREATE TABLE bad_events (
    event_id BIGSERIAL,
    data JSONB            -- When was this loaded? From where?
);
*/

-- ─── ✅ Correct Patterns ─────────────────────────────────────────
-- See the silver.* and gold.* tables in docker/postgres/init.sql
-- for real-world examples with constraints and audit columns.
