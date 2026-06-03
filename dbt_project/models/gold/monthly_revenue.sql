/* ============================================================
   SQLMesh Model: gold__monthly_revenue
   Layer:         Gold
   Type:          FULL (full refresh, idempotent)

   Equivalent to a dbt model with materialized='table'

   Run:  sqlmesh run
   Test: sqlmesh test
   Plan: sqlmesh plan
   ============================================================ */

MODEL (
    name gold.monthly_revenue_sqlmesh,
    kind FULL,
    cron '@daily',
    grain (year_month),
    description 'Monthly revenue KPIs with MoM growth, computed by SQLMesh'
);

WITH daily AS (
    SELECT
        TO_CHAR(revenue_date, 'YYYY-MM')            AS year_month,
        EXTRACT(YEAR FROM revenue_date)::INT         AS year,
        EXTRACT(MONTH FROM revenue_date)::INT        AS month,
        SUM(order_count)                             AS order_count,
        SUM(gross_revenue)                           AS gross_revenue,
        SUM(net_revenue)                             AS net_revenue,
        ROUND(AVG(avg_order_value)::NUMERIC, 2)      AS avg_order_value,
        SUM(unique_customers)                        AS unique_customers
    FROM gold.daily_revenue
    GROUP BY 1, 2, 3
),

with_lag AS (
    SELECT
        *,
        LAG(gross_revenue) OVER (ORDER BY year_month)  AS prev_month_revenue
    FROM daily
)

SELECT
    year_month,
    year,
    month,
    order_count,
    gross_revenue,
    net_revenue,
    avg_order_value,
    CASE
        WHEN prev_month_revenue IS NOT NULL AND prev_month_revenue > 0
        THEN ROUND(
            ((gross_revenue - prev_month_revenue) / prev_month_revenue * 100)::NUMERIC,
        2)
        ELSE NULL
    END                                              AS mom_growth_pct,
    unique_customers,
    NOW()                                            AS _computed_at
FROM with_lag
ORDER BY year_month
