-- ================================================================
--  SQL Module — Data Engineering Playground
--  File: sql/queries/03_window_functions.sql
--  Topic: Window Functions (essential for analytics engineering)
-- ================================================================

-- ─── What are Window Functions? ─────────────────────────────────
-- They perform calculations ACROSS rows related to the current row
-- WITHOUT collapsing them like GROUP BY does.
-- Syntax: function() OVER (PARTITION BY ... ORDER BY ...)

-- ─── Setup: reference tables ────────────────────────────────────

-- Example 1: Running total of revenue by date
SELECT
    revenue_date,
    gross_revenue,
    -- Running cumulative sum
    SUM(gross_revenue) OVER (
        ORDER BY revenue_date
        ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
    )                                       AS running_total,

    -- 7-day rolling average
    ROUND(AVG(gross_revenue) OVER (
        ORDER BY revenue_date
        ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
    ), 2)                                   AS rolling_7d_avg

FROM gold.daily_revenue
ORDER BY revenue_date;


-- Example 2: Rank customers by revenue within their tier
SELECT
    full_name,
    tier,
    total_revenue,

    -- Rank within tier (1 = highest revenue)
    RANK() OVER (
        PARTITION BY tier
        ORDER BY total_revenue DESC
    )                                       AS rank_in_tier,

    -- Overall rank
    RANK() OVER (
        ORDER BY total_revenue DESC
    )                                       AS overall_rank,

    -- Percentile within tier (0–1)
    ROUND(PERCENT_RANK() OVER (
        PARTITION BY tier
        ORDER BY total_revenue
    )::NUMERIC, 3)                          AS percentile_in_tier

FROM gold.customer_ltv
WHERE total_orders > 0
ORDER BY tier, rank_in_tier;


-- Example 3: Month-over-Month comparison using LAG
SELECT
    year_month,
    gross_revenue,

    -- Previous month
    LAG(gross_revenue, 1) OVER (ORDER BY year_month)    AS prev_month,

    -- Same month last year
    LAG(gross_revenue, 12) OVER (ORDER BY year_month)   AS same_month_last_year,

    -- MoM growth %
    CASE
        WHEN LAG(gross_revenue, 1) OVER (ORDER BY year_month) > 0
        THEN ROUND(
            (gross_revenue - LAG(gross_revenue, 1) OVER (ORDER BY year_month))
            / LAG(gross_revenue, 1) OVER (ORDER BY year_month) * 100
        , 1)
    END                                                 AS mom_growth_pct,

    -- YoY growth %
    CASE
        WHEN LAG(gross_revenue, 12) OVER (ORDER BY year_month) > 0
        THEN ROUND(
            (gross_revenue - LAG(gross_revenue, 12) OVER (ORDER BY year_month))
            / LAG(gross_revenue, 12) OVER (ORDER BY year_month) * 100
        , 1)
    END                                                 AS yoy_growth_pct

FROM gold.monthly_revenue
ORDER BY year_month;


-- Example 4: First & last order per customer (useful for cohort analysis)
SELECT
    customer_id,
    order_id,
    order_date,
    total_amount,

    FIRST_VALUE(order_date) OVER w      AS first_order_date,
    LAST_VALUE(order_date)  OVER w      AS last_order_date,

    -- Order sequence number
    ROW_NUMBER() OVER (
        PARTITION BY customer_id
        ORDER BY order_date
    )                                   AS order_number,

    -- Days between orders
    order_date - LAG(order_date) OVER (
        PARTITION BY customer_id
        ORDER BY order_date
    )                                   AS days_since_last_order

FROM silver.orders
WHERE status = 'completed'
WINDOW w AS (
    PARTITION BY customer_id
    ORDER BY order_date
    ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING
)
ORDER BY customer_id, order_date;


-- ================================================================
--  📚 EXERCISES
-- ================================================================

-- Exercise 1 ⭐
-- Using gold.daily_revenue, calculate a 30-day rolling average of revenue.
-- Expected columns: revenue_date, gross_revenue, rolling_30d_avg
-- Hint: ROWS BETWEEN 29 PRECEDING AND CURRENT ROW

-- Exercise 2 ⭐⭐
-- Find the top 3 products by revenue IN EACH category.
-- Expected columns: category, product_name, total_revenue, rank_in_category
-- Hint: RANK() OVER (PARTITION BY category ORDER BY total_revenue DESC)

-- Exercise 3 ⭐⭐⭐
-- For each customer, find their "best month" (highest spending month).
-- Expected columns: customer_id, best_month, month_revenue, total_ltv
-- Hint: Use a CTE to aggregate by customer+month, then RANK()
