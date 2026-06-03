"""
gold/aggregate_kpis.py — Silver → Gold KPI computation.

Idempotency strategy for Gold: TRUNCATE + INSERT
  Why? Gold tables are full aggregations — it's cheaper and safer
  to recompute everything than to track incremental changes.
  Since it runs in a transaction, there's no window of missing data.
"""

import logging

log = logging.getLogger(__name__)


def compute_daily_revenue(hook) -> int:
    """
    Compute daily revenue KPIs and load into gold.daily_revenue.

    Idempotent: TRUNCATE inside a transaction then INSERT.
    """
    sql = """
    BEGIN;

    TRUNCATE TABLE gold.daily_revenue;

    INSERT INTO gold.daily_revenue
        (revenue_date, order_count, gross_revenue, net_revenue,
         avg_order_value, unique_customers, new_customers)
    SELECT
        o.order_date                                    AS revenue_date,
        COUNT(DISTINCT o.order_id)                      AS order_count,
        SUM(oi.line_total)                              AS gross_revenue,
        -- net: exclude cancelled and refunded
        SUM(CASE WHEN o.status NOT IN ('cancelled','refunded')
                 THEN oi.line_total ELSE 0 END)         AS net_revenue,
        ROUND(AVG(o.total_amount), 2)                   AS avg_order_value,
        COUNT(DISTINCT o.customer_id)                   AS unique_customers,
        -- new customers: first order on this date
        COUNT(DISTINCT CASE
            WHEN o.order_date = first_orders.first_date
            THEN o.customer_id
        END)                                            AS new_customers
    FROM silver.orders o
    JOIN silver.order_items oi ON o.order_id = oi.order_id
    LEFT JOIN (
        SELECT customer_id, MIN(order_date) AS first_date
        FROM silver.orders
        GROUP BY customer_id
    ) first_orders ON o.customer_id = first_orders.customer_id
    GROUP BY o.order_date
    ORDER BY o.order_date;

    COMMIT;
    """
    hook.run(sql)
    row = hook.get_first("SELECT COUNT(*) FROM gold.daily_revenue")
    return row[0] if row else 0


def compute_monthly_revenue(hook) -> int:
    """Compute monthly rollup with Month-over-Month growth."""
    sql = """
    BEGIN;

    TRUNCATE TABLE gold.monthly_revenue;

    WITH monthly AS (
        SELECT
            TO_CHAR(revenue_date, 'YYYY-MM')  AS year_month,
            EXTRACT(YEAR FROM revenue_date)::INT AS year,
            EXTRACT(MONTH FROM revenue_date)::INT AS month,
            SUM(order_count)                  AS order_count,
            SUM(gross_revenue)                AS gross_revenue,
            SUM(net_revenue)                  AS net_revenue,
            ROUND(AVG(avg_order_value), 2)    AS avg_order_value,
            SUM(unique_customers)             AS unique_customers
        FROM gold.daily_revenue
        GROUP BY 1, 2, 3
    )
    INSERT INTO gold.monthly_revenue
        (year_month, year, month, order_count, gross_revenue, net_revenue,
         avg_order_value, mom_growth_pct, unique_customers)
    SELECT
        m.year_month,
        m.year,
        m.month,
        m.order_count,
        m.gross_revenue,
        m.net_revenue,
        m.avg_order_value,
        -- MoM growth %
        CASE WHEN prev.gross_revenue > 0
             THEN ROUND(
                 ((m.gross_revenue - prev.gross_revenue) / prev.gross_revenue) * 100
             , 2)
             ELSE NULL
        END                                   AS mom_growth_pct,
        m.unique_customers
    FROM monthly m
    LEFT JOIN monthly prev
        ON prev.year  = m.year
        AND prev.month = m.month - 1
        OR (prev.year = m.year - 1 AND m.month = 1 AND prev.month = 12)
    ORDER BY m.year_month;

    COMMIT;
    """
    hook.run(sql)
    row = hook.get_first("SELECT COUNT(*) FROM gold.monthly_revenue")
    return row[0] if row else 0


def compute_customer_ltv(hook) -> int:
    """
    Compute Customer Lifetime Value and segment customers.

    Segments:
      - HIGH: total_revenue >= $1000
      - MEDIUM: $200 <= total_revenue < $1000
      - LOW: total_revenue < $200 AND last order < 180 days ago
      - CHURNED: last order >= 180 days ago
    """
    sql = """
    BEGIN;

    TRUNCATE TABLE gold.customer_ltv;

    INSERT INTO gold.customer_ltv
        (customer_id, full_name, email, tier, country,
         first_order_date, last_order_date, total_orders,
         total_revenue, avg_order_value, days_since_last, ltv_segment)
    SELECT
        c.customer_id,
        c.full_name,
        c.email,
        c.tier,
        c.country,
        MIN(o.order_date)                               AS first_order_date,
        MAX(o.order_date)                               AS last_order_date,
        COUNT(DISTINCT o.order_id)                      AS total_orders,
        COALESCE(SUM(oi.line_total), 0)                 AS total_revenue,
        ROUND(AVG(o.total_amount), 2)                   AS avg_order_value,
        (CURRENT_DATE - MAX(o.order_date))::INT         AS days_since_last,

        CASE
            WHEN (CURRENT_DATE - MAX(o.order_date)) >= 180 THEN 'CHURNED'
            WHEN SUM(oi.line_total) >= 1000              THEN 'HIGH'
            WHEN SUM(oi.line_total) >= 200               THEN 'MEDIUM'
            ELSE 'LOW'
        END                                             AS ltv_segment

    FROM silver.customers c
    LEFT JOIN silver.orders o
        ON c.customer_id = o.customer_id
        AND o.status NOT IN ('cancelled', 'refunded')
    LEFT JOIN silver.order_items oi
        ON o.order_id = oi.order_id
    GROUP BY c.customer_id, c.full_name, c.email, c.tier, c.country
    ORDER BY total_revenue DESC;

    COMMIT;
    """
    hook.run(sql)
    row = hook.get_first("SELECT COUNT(*) FROM gold.customer_ltv")
    return row[0] if row else 0


def compute_product_performance(hook) -> int:
    """Compute product sales performance and rank within category."""
    sql = """
    BEGIN;

    TRUNCATE TABLE gold.product_performance;

    WITH product_sales AS (
        SELECT
            p.product_id,
            p.product_name,
            p.category,
            SUM(oi.quantity)                AS total_units_sold,
            SUM(oi.line_total)              AS total_revenue,
            SUM(oi.quantity * p.cost)       AS total_cost,
            COUNT(DISTINCT o.order_id)      AS order_count,
            ROUND(AVG(oi.unit_price), 2)    AS avg_selling_price
        FROM silver.products p
        LEFT JOIN silver.order_items oi ON p.product_id = oi.product_id
        LEFT JOIN silver.orders o
            ON oi.order_id = o.order_id
            AND o.status NOT IN ('cancelled', 'refunded')
        GROUP BY p.product_id, p.product_name, p.category
    )
    INSERT INTO gold.product_performance
        (product_id, product_name, category, total_units_sold,
         total_revenue, total_profit, order_count, avg_selling_price,
         revenue_rank, category_rank)
    SELECT
        product_id,
        product_name,
        category,
        COALESCE(total_units_sold, 0),
        COALESCE(total_revenue, 0),
        COALESCE(total_revenue - total_cost, 0)     AS total_profit,
        COALESCE(order_count, 0),
        avg_selling_price,
        RANK() OVER (ORDER BY total_revenue DESC NULLS LAST)           AS revenue_rank,
        RANK() OVER (
            PARTITION BY category
            ORDER BY total_revenue DESC NULLS LAST
        )                                                              AS category_rank
    FROM product_sales;

    COMMIT;
    """
    hook.run(sql)
    row = hook.get_first("SELECT COUNT(*) FROM gold.product_performance")
    return row[0] if row else 0
