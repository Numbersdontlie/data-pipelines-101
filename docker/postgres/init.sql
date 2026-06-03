-- =============================================================
--  Data Engineering Playground — Warehouse Init
--  Creates: schemas, tables, roles
-- =============================================================

-- ─── Schemas (Medallion Layers) ───────────────────────────────
CREATE SCHEMA IF NOT EXISTS bronze;
CREATE SCHEMA IF NOT EXISTS silver;
CREATE SCHEMA IF NOT EXISTS gold;
CREATE SCHEMA IF NOT EXISTS staging;

-- ─── Extensions ───────────────────────────────────────────────
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- =============================================================
--  BRONZE LAYER — Raw, untransformed ingestion
-- =============================================================

CREATE TABLE IF NOT EXISTS bronze.raw_orders (
    _id              BIGSERIAL PRIMARY KEY,
    _ingested_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    _source_file     TEXT,
    _batch_id        TEXT,
    -- Raw columns (all TEXT to preserve exactly what came in)
    order_id         TEXT,
    customer_id      TEXT,
    order_date       TEXT,
    status           TEXT,
    total_amount     TEXT,
    currency         TEXT,
    created_at       TEXT
);

CREATE TABLE IF NOT EXISTS bronze.raw_customers (
    _id              BIGSERIAL PRIMARY KEY,
    _ingested_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    _source_file     TEXT,
    _batch_id        TEXT,
    customer_id      TEXT,
    first_name       TEXT,
    last_name        TEXT,
    email            TEXT,
    country          TEXT,
    signup_date      TEXT,
    tier             TEXT
);

CREATE TABLE IF NOT EXISTS bronze.raw_products (
    _id              BIGSERIAL PRIMARY KEY,
    _ingested_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    _source_file     TEXT,
    _batch_id        TEXT,
    product_id       TEXT,
    product_name     TEXT,
    category         TEXT,
    price            TEXT,
    cost             TEXT,
    stock_qty        TEXT
);

CREATE TABLE IF NOT EXISTS bronze.raw_order_items (
    _id              BIGSERIAL PRIMARY KEY,
    _ingested_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    _source_file     TEXT,
    _batch_id        TEXT,
    order_item_id    TEXT,
    order_id         TEXT,
    product_id       TEXT,
    quantity         TEXT,
    unit_price       TEXT,
    discount         TEXT
);

-- Pipeline audit log (tracks every run)
CREATE TABLE IF NOT EXISTS bronze.pipeline_runs (
    run_id           UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    pipeline_name    TEXT NOT NULL,
    layer            TEXT NOT NULL,
    status           TEXT NOT NULL, -- RUNNING, SUCCESS, FAILED
    rows_processed   INTEGER,
    rows_inserted    INTEGER,
    rows_updated     INTEGER,
    started_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    finished_at      TIMESTAMPTZ,
    error_message    TEXT,
    metadata         JSONB
);

-- =============================================================
--  SILVER LAYER — Cleaned, typed, deduplicated
-- =============================================================

CREATE TABLE IF NOT EXISTS silver.orders (
    order_id         UUID PRIMARY KEY,
    customer_id      UUID NOT NULL,
    order_date       DATE NOT NULL,
    status           TEXT NOT NULL,
    total_amount     NUMERIC(12, 2) NOT NULL,
    currency         CHAR(3) NOT NULL DEFAULT 'EUR',
    created_at       TIMESTAMPTZ,
    -- Data quality metadata
    _source_batch    TEXT,
    _silver_loaded_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    _is_valid        BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE IF NOT EXISTS silver.customers (
    customer_id      UUID PRIMARY KEY,
    first_name       TEXT NOT NULL,
    last_name        TEXT NOT NULL,
    email            TEXT UNIQUE NOT NULL,
    country          TEXT,
    signup_date      DATE,
    tier             TEXT CHECK (tier IN ('bronze', 'silver', 'gold', 'platinum')),
    full_name        TEXT GENERATED ALWAYS AS (first_name || ' ' || last_name) STORED,
    _source_batch    TEXT,
    _silver_loaded_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS silver.products (
    product_id       UUID PRIMARY KEY,
    product_name     TEXT NOT NULL,
    category         TEXT,
    price            NUMERIC(10, 2) NOT NULL,
    cost             NUMERIC(10, 2),
    margin_pct       NUMERIC(5, 2) GENERATED ALWAYS AS (
                         CASE WHEN price > 0
                         THEN ROUND(((price - cost) / price) * 100, 2)
                         ELSE NULL END
                     ) STORED,
    stock_qty        INTEGER,
    _source_batch    TEXT,
    _silver_loaded_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS silver.order_items (
    order_item_id    UUID PRIMARY KEY,
    order_id         UUID NOT NULL REFERENCES silver.orders(order_id),
    product_id       UUID NOT NULL REFERENCES silver.products(product_id),
    quantity         INTEGER NOT NULL,
    unit_price       NUMERIC(10, 2) NOT NULL,
    discount         NUMERIC(5, 2) DEFAULT 0,
    line_total       NUMERIC(12, 2) GENERATED ALWAYS AS (
                         quantity * unit_price * (1 - discount / 100)
                     ) STORED,
    _source_batch    TEXT,
    _silver_loaded_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- =============================================================
--  GOLD LAYER — Business-ready aggregations & KPIs
-- =============================================================

-- Daily revenue KPI
CREATE TABLE IF NOT EXISTS gold.daily_revenue (
    revenue_date     DATE PRIMARY KEY,
    order_count      INTEGER NOT NULL,
    gross_revenue    NUMERIC(15, 2) NOT NULL,
    net_revenue      NUMERIC(15, 2) NOT NULL,
    avg_order_value  NUMERIC(10, 2) NOT NULL,
    unique_customers INTEGER NOT NULL,
    new_customers    INTEGER NOT NULL DEFAULT 0,
    _computed_at     TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Monthly revenue KPI
CREATE TABLE IF NOT EXISTS gold.monthly_revenue (
    year_month       CHAR(7) PRIMARY KEY,  -- YYYY-MM
    year             INTEGER NOT NULL,
    month            INTEGER NOT NULL,
    order_count      INTEGER NOT NULL,
    gross_revenue    NUMERIC(15, 2) NOT NULL,
    net_revenue      NUMERIC(15, 2) NOT NULL,
    avg_order_value  NUMERIC(10, 2) NOT NULL,
    mom_growth_pct   NUMERIC(6, 2),         -- Month-over-Month growth
    unique_customers INTEGER NOT NULL,
    _computed_at     TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Customer Lifetime Value
CREATE TABLE IF NOT EXISTS gold.customer_ltv (
    customer_id      UUID PRIMARY KEY,
    full_name        TEXT,
    email            TEXT,
    tier             TEXT,
    country          TEXT,
    first_order_date DATE,
    last_order_date  DATE,
    total_orders     INTEGER NOT NULL DEFAULT 0,
    total_revenue    NUMERIC(15, 2) NOT NULL DEFAULT 0,
    avg_order_value  NUMERIC(10, 2),
    days_since_last  INTEGER,
    ltv_segment      TEXT,  -- HIGH, MEDIUM, LOW, CHURNED
    _computed_at     TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Product performance
CREATE TABLE IF NOT EXISTS gold.product_performance (
    product_id       UUID PRIMARY KEY,
    product_name     TEXT NOT NULL,
    category         TEXT,
    total_units_sold INTEGER NOT NULL DEFAULT 0,
    total_revenue    NUMERIC(15, 2) NOT NULL DEFAULT 0,
    total_profit     NUMERIC(15, 2),
    order_count      INTEGER NOT NULL DEFAULT 0,
    avg_selling_price NUMERIC(10, 2),
    revenue_rank     INTEGER,
    category_rank    INTEGER,
    _computed_at     TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- =============================================================
--  INDEXES
-- =============================================================

-- Bronze
CREATE INDEX IF NOT EXISTS idx_bronze_orders_batch ON bronze.raw_orders(_batch_id);
CREATE INDEX IF NOT EXISTS idx_bronze_orders_ingested ON bronze.raw_orders(_ingested_at);

-- Silver
CREATE INDEX IF NOT EXISTS idx_silver_orders_customer ON silver.orders(customer_id);
CREATE INDEX IF NOT EXISTS idx_silver_orders_date ON silver.orders(order_date);
CREATE INDEX IF NOT EXISTS idx_silver_orders_status ON silver.orders(status);
CREATE INDEX IF NOT EXISTS idx_silver_items_order ON silver.order_items(order_id);
CREATE INDEX IF NOT EXISTS idx_silver_items_product ON silver.order_items(product_id);

-- Gold
CREATE INDEX IF NOT EXISTS idx_gold_rev_date ON gold.daily_revenue(revenue_date);
CREATE INDEX IF NOT EXISTS idx_gold_ltv_segment ON gold.customer_ltv(ltv_segment);

-- =============================================================
--  HELPER VIEWS (useful for learning)
-- =============================================================

CREATE OR REPLACE VIEW silver.v_order_summary AS
SELECT
    o.order_id,
    o.order_date,
    o.status,
    o.total_amount,
    c.full_name AS customer_name,
    c.email,
    c.tier,
    c.country,
    COUNT(oi.order_item_id) AS item_count,
    SUM(oi.line_total)      AS calculated_total
FROM silver.orders o
JOIN silver.customers c  ON o.customer_id = c.customer_id
JOIN silver.order_items oi ON o.order_id  = oi.order_id
GROUP BY o.order_id, o.order_date, o.status, o.total_amount,
         c.full_name, c.email, c.tier, c.country;

COMMENT ON VIEW silver.v_order_summary IS 'Denormalized order view for easier analysis';

-- =============================================================
--  NOTIFY
-- =============================================================
DO $$
BEGIN
    RAISE NOTICE '✅ Warehouse schemas and tables created successfully!';
    RAISE NOTICE '   Schemas: bronze, silver, gold, staging';
END $$;
