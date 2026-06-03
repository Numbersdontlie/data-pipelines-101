"""
medallion_pipeline.py — Full Bronze → Silver → Gold pipeline DAG.

This DAG demonstrates:
  - Medallion architecture orchestration
  - Idempotent task design
  - Error handling & retries
  - Pipeline audit logging
  - Task dependencies
"""

from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.empty import EmptyOperator
from airflow.providers.postgres.hooks.postgres import PostgresHook
from airflow.utils.dates import days_ago

# ─── Default Args ──────────────────────────────────────────────
default_args = {
    "owner": "playground",
    "retries": 2,
    "retry_delay": timedelta(minutes=2),
    "email_on_failure": False,
}

# ─── DAG Definition ────────────────────────────────────────────
with DAG(
    dag_id="medallion_pipeline",
    description="Bronze → Silver → Gold medallion pipeline",
    schedule_interval="0 6 * * *",   # Daily at 06:00 UTC
    start_date=days_ago(1),
    catchup=False,
    default_args=default_args,
    tags=["medallion", "etl", "playground"],
    doc_md="""
## Medallion Pipeline

Full end-to-end pipeline following the medallion architecture:

1. **Bronze** — Validate raw data ingestion (data already in bronze from seed or upstream)
2. **Silver** — Clean, type-cast, deduplicate
3. **Gold**   — Compute KPIs and aggregations

### Idempotency strategy
- Silver: `INSERT ... ON CONFLICT DO UPDATE` (UPSERT by PK)
- Gold: `TRUNCATE + INSERT` (full daily recompute)
    """,
) as dag:

    # ── Start marker ──────────────────────────────────────────
    start = EmptyOperator(task_id="start")
    end   = EmptyOperator(task_id="end")

    # ── Bronze validation ─────────────────────────────────────
    def validate_bronze(**ctx):
        """Check raw tables have data before proceeding with the extraction."""
        hook = PostgresHook(postgres_conn_id="postgres_playground")
        tables = ["bronze.raw_orders", "bronze.raw_customers",
                  "bronze.raw_products", "bronze.raw_order_items"]
        results = {}
        for t in tables:
            row = hook.get_first(f"SELECT COUNT(*) FROM {t}")
            count = row[0]
            results[t] = count
            print(f"  {t}: {count:,} rows")
            if count == 0:
                raise ValueError(
                    f"Bronze table {t} is empty! Run seed_data.py first to populate tables."
                )
        return results

    bronze_validate = PythonOperator(
        task_id="bronze_validate",
        python_callable=validate_bronze,
        doc_md="Validates bronze tables are non-empty before transform.",
    )

    # ── Silver: Customers ─────────────────────────────────────
    def silver_load_customers(**ctx):
        """
        Idempotent UPSERT from bronze → silver for customers.
        Uses INSERT ... ON CONFLICT DO UPDATE to handle reruns safely.
        """
        from pipelines.silver.clean_transform import load_customers
        hook = PostgresHook(postgres_conn_id="postgres_playground")
        rows_upserted = load_customers(hook)
        print(f"  Customers upserted: {rows_upserted:,}")
        return rows_upserted

    silver_customers = PythonOperator(
        task_id="silver_customers",
        python_callable=silver_load_customers,
        doc_md="Cleans and loads customers into silver layer.",
    )

    # ── Silver: Products ──────────────────────────────────────
    def silver_load_products(**ctx):
        from pipelines.silver.clean_transform import load_products
        hook = PostgresHook(postgres_conn_id="postgres_playground")
        rows_upserted = load_products(hook)
        print(f"  Products upserted: {rows_upserted:,}")
        return rows_upserted

    silver_products = PythonOperator(
        task_id="silver_products",
        python_callable=silver_load_products,
    )

    # ── Silver: Orders ────────────────────────────────────────
    def silver_load_orders(**ctx):
        from pipelines.silver.clean_transform import load_orders
        hook = PostgresHook(postgres_conn_id="postgres_playground")
        rows_upserted = load_orders(hook)
        print(f"  Orders upserted: {rows_upserted:,}")
        return rows_upserted

    silver_orders = PythonOperator(
        task_id="silver_orders",
        python_callable=silver_load_orders,
    )

    # ── Silver: Order Items ───────────────────────────────────
    def silver_load_order_items(**ctx):
        from pipelines.silver.clean_transform import load_order_items
        hook = PostgresHook(postgres_conn_id="postgres_playground")
        rows_upserted = load_order_items(hook)
        print(f"  Order items upserted: {rows_upserted:,}")
        return rows_upserted

    silver_order_items = PythonOperator(
        task_id="silver_order_items",
        python_callable=silver_load_order_items,
    )

    # ── Gold: Daily Revenue ───────────────────────────────────
    def gold_daily_revenue(**ctx):
        from pipelines.gold.aggregate_kpis import compute_daily_revenue
        hook = PostgresHook(postgres_conn_id="postgres_playground")
        rows = compute_daily_revenue(hook)
        print(f"  Daily revenue rows: {rows:,}")
        return rows

    gold_revenue = PythonOperator(
        task_id="gold_daily_revenue",
        python_callable=gold_daily_revenue,
        doc_md="Full refresh of gold.daily_revenue. Idempotent: TRUNCATE + INSERT.",
    )

    # ── Gold: Monthly Revenue ─────────────────────────────────
    def gold_monthly_revenue(**ctx):
        from pipelines.gold.aggregate_kpis import compute_monthly_revenue
        hook = PostgresHook(postgres_conn_id="postgres_playground")
        rows = compute_monthly_revenue(hook)
        print(f"  Monthly revenue rows: {rows:,}")
        return rows

    gold_monthly = PythonOperator(
        task_id="gold_monthly_revenue",
        python_callable=gold_monthly_revenue,
    )

    # ── Gold: Customer LTV ────────────────────────────────────
    def gold_customer_ltv(**ctx):
        from pipelines.gold.aggregate_kpis import compute_customer_ltv
        hook = PostgresHook(postgres_conn_id="postgres_playground")
        rows = compute_customer_ltv(hook)
        print(f"  Customer LTV rows: {rows:,}")
        return rows

    gold_ltv = PythonOperator(
        task_id="gold_customer_ltv",
        python_callable=gold_customer_ltv,
    )

    # ── Gold: Product Performance ─────────────────────────────
    def gold_product_perf(**ctx):
        from pipelines.gold.aggregate_kpis import compute_product_performance
        hook = PostgresHook(postgres_conn_id="postgres_playground")
        rows = compute_product_performance(hook)
        print(f"  Product performance rows: {rows:,}")
        return rows

    gold_products = PythonOperator(
        task_id="gold_product_performance",
        python_callable=gold_product_perf,
    )

    # ── Log pipeline success ──────────────────────────────────
    def log_success(**ctx):
        hook = PostgresHook(postgres_conn_id="postgres_playground")
        hook.run("""
            INSERT INTO bronze.pipeline_runs
                (pipeline_name, layer, status, finished_at)
            VALUES ('medallion_pipeline', 'all', 'SUCCESS', NOW())
        """)
        print("🏆 Pipeline completed successfully!")

    log_run = PythonOperator(
        task_id="log_pipeline_success",
        python_callable=log_success,
    )

    # ─── Task Dependencies ─────────────────────────────────────
    #
    #  start
    #    └── bronze_validate
    #          ├── silver_customers ──┐
    #          └── silver_products ──┤
    #                                ├── silver_orders
    #                                │     └── silver_order_items
    #                                │           ├── gold_daily_revenue
    #                                │           ├── gold_monthly_revenue
    #                                │           ├── gold_customer_ltv
    #                                │           └── gold_product_performance
    #                                │                 └── log_run
    #                                │                       └── end

    start >> bronze_validate
    bronze_validate >> [silver_customers, silver_products]
    [silver_customers, silver_products] >> silver_orders
    silver_orders >> silver_order_items
    silver_order_items >> [gold_revenue, gold_monthly, gold_ltv, gold_products]
    [gold_revenue, gold_monthly, gold_ltv, gold_products] >> log_run >> end
