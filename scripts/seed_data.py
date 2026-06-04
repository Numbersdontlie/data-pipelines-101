"""
seed_data.py — Generate and load synthetic e-commerce data into Bronze layer.

Usage:
    python scripts/seed_data.py [--rows 50000]
"""

import os
import uuid
import random
import argparse
from datetime import datetime, timedelta, date

import psycopg2
from psycopg2.extras import execute_batch
from faker import Faker

fake = Faker()
Faker.seed(42)
random.seed(42)

# ─── Config ────────────────────────────────────────────────────
DB_CONFIG = {
    "host": os.getenv("POSTGRES_HOST", "localhost"),
    "port": int(os.getenv("POSTGRES_PORT", 5432)),
    "user": os.getenv("POSTGRES_USER", "playground"),
    "password": os.getenv("POSTGRES_PASSWORD", "playground"),
    "dbname": os.getenv("POSTGRES_DB", "warehouse"),
}

BATCH_ID = datetime.utcnow().strftime("seed_%Y%m%d_%H%M%S")

CATEGORIES = ["Electronics", "Clothing", "Home & Garden", "Sports", "Books", "Toys", "Beauty", "Food"]
STATUSES = ["completed", "completed", "completed", "shipped", "processing", "cancelled", "refunded"]
TIERS = ["bronze", "bronze", "silver", "silver", "gold", "platinum"]
CURRENCIES = ["USD", "USD", "USD", "EUR", "GBP"]


def get_conn():
    return psycopg2.connect(**DB_CONFIG)


def seed_customers(conn, n: int = 10_000) -> list[str]:
    """Generate synthetic customer data and insert into bronze.raw_customers."""
    print(f"  Seeding {n:,} customers...")
    ids = [str(uuid.uuid4()) for _ in range(n)]
    rows = []
    base_date = date(2020, 1, 1)

    for cid in ids:
        signup = base_date + timedelta(days=random.randint(0, 1460))
        rows.append((
            BATCH_ID, "seed_data.py",
            cid,
            fake.first_name(),
            fake.last_name(),
            fake.unique.email(),
            fake.country_code(),
            signup.isoformat(),
            random.choice(TIERS),
        ))

    sql = """
        INSERT INTO bronze.raw_customers
            (_batch_id, _source_file, customer_id, first_name, last_name,
             email, country, signup_date, tier)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT DO NOTHING
    """
    with conn.cursor() as cur:
        execute_batch(cur, sql, rows, page_size=1000)
    conn.commit()
    print(f"  ✅ {n:,} customers inserted")
    return ids


def seed_products(conn, n: int = 500) -> list[str]:
    """Generate synthetic product catalog."""
    print(f"  Seeding {n:,} products...")
    ids = [str(uuid.uuid4()) for _ in range(n)]
    rows = []

    for pid in ids:
        cost = round(random.uniform(2.0, 200.0), 2)
        price = round(cost * random.uniform(1.2, 3.5), 2)
        rows.append((
            BATCH_ID, "seed_data.py",
            pid,
            fake.bs().title()[:60],
            random.choice(CATEGORIES),
            str(price),
            str(cost),
            str(random.randint(0, 5000)),
        ))

    sql = """
        INSERT INTO bronze.raw_products
            (_batch_id, _source_file, product_id, product_name, category,
             price, cost, stock_qty)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT DO NOTHING
    """
    with conn.cursor() as cur:
        execute_batch(cur, sql, rows, page_size=500)
    conn.commit()
    print(f"  ✅ {n:,} products inserted")
    return ids


def seed_orders(conn, customer_ids: list, n: int = 50_000) -> list[str]:
    """Generate order transactions."""
    print(f"  Seeding {n:,} orders...")
    order_ids = [str(uuid.uuid4()) for _ in range(n)]
    rows = []
    base_date = datetime(2021, 1, 1)

    for oid in order_ids:
        created = base_date + timedelta(
            days=random.randint(0, 1095),
            hours=random.randint(0, 23),
            minutes=random.randint(0, 59)
        )
        rows.append((
            BATCH_ID, "seed_data.py",
            oid,
            random.choice(customer_ids),
            created.date().isoformat(),
            random.choice(STATUSES),
            str(round(random.uniform(10.0, 2000.0), 2)),
            random.choice(CURRENCIES),
            created.isoformat(),
        ))

    sql = """
        INSERT INTO bronze.raw_orders
            (_batch_id, _source_file, order_id, customer_id, order_date,
             status, total_amount, currency, created_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT DO NOTHING
    """
    with conn.cursor() as cur:
        execute_batch(cur, sql, rows, page_size=1000)
    conn.commit()
    print(f"  ✅ {n:,} orders inserted")
    return order_ids


def seed_order_items(conn, order_ids: list, product_ids: list):
    """Generate order line items (1–5 items per order)."""
    print(f"  Seeding order items...")
    rows = []

    for oid in order_ids:
        n_items = random.randint(1, 5)
        selected_products = random.sample(product_ids, min(n_items, len(product_ids)))
        for pid in selected_products:
            rows.append((
                BATCH_ID, "seed_data.py",
                str(uuid.uuid4()),
                oid,
                pid,
                str(random.randint(1, 10)),
                str(round(random.uniform(5.0, 500.0), 2)),
                str(round(random.choice([0, 0, 0, 5, 10, 15, 20]), 2)),
            ))

    sql = """
        INSERT INTO bronze.raw_order_items
            (_batch_id, _source_file, order_item_id, order_id, product_id,
             quantity, unit_price, discount)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT DO NOTHING
    """
    with conn.cursor() as cur:
        execute_batch(cur, sql, rows, page_size=2000)
    conn.commit()
    print(f"  ✅ {len(rows):,} order items inserted")


def main(n_orders: int = 50_000):
    print("\n🌱 Data Engineering Playground — Seed Script")
    print("=" * 50)
    print(f"  Batch ID : {BATCH_ID}")
    print(f"  Target   : {n_orders:,} orders")
    print(f"  DB       : {DB_CONFIG['dbname']}@{DB_CONFIG['host']}")
    print()

    conn = get_conn()
    try:
        customer_ids = seed_customers(conn, n=10_000)
        product_ids  = seed_products(conn, n=500)
        order_ids    = seed_orders(conn, customer_ids, n=n_orders)
        seed_order_items(conn, order_ids, product_ids)
    finally:
        conn.close()

    print()
    print("✅ Seed complete! Now trigger the Airflow DAG:")
    print("   airflow dags trigger medallion_pipeline")
    print()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed synthetic data into the playground warehouse")
    parser.add_argument("--rows", type=int, default=50_000, help="Number of orders to generate")
    args = parser.parse_args()
    main(n_orders=args.rows)
