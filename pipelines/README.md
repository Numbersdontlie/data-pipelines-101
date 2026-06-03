# 🔄 Pipelines — Medallion Architecture

This module walks you through the industry-standard **Bronze → Silver → Gold** (Medallion) architecture.

---

## The Pattern

```
External Data Source
        │
        ▼
┌──────────────┐
│    BRONZE    │  Raw ingestion — exact copy of source, all TEXT columns
│  (raw layer) │  Never transform here. Just land the data.
└──────┬───────┘
       │
       ▼
┌──────────────┐
│    SILVER    │  Cleaned, typed, deduplicated
│ (clean layer)│  Cast types, validate, remove duplicates
└──────┬───────┘
       │
       ▼
┌──────────────┐
│     GOLD     │  Business-ready KPIs & aggregations
│(business layer) Serve to dashboards, analysts, data scientists
└──────────────┘
```

---

## Why This Pattern?

| Concern | How Medallion Solves It |
|---|---|
| **Debugging** | Bronze preserves the raw data — you can always reprocess |
| **Data Quality** | Silver validates before Gold uses it |
| **Separation of concerns** | Bronze = infra, Silver = engineering, Gold = business |
| **Re-runability** | Each layer is independently rerunnable |
| **Auditability** | `_ingested_at`, `_batch_id`, `_silver_loaded_at` columns |

---

## Idempotency

> **"Running a pipeline N times produces the same result as running it once."**

This is the most important concept in production data engineering. See [`idempotency/patterns.py`](idempotency/patterns.py) for 4 patterns with examples.

### Quick Reference

| Layer | Pattern | Why |
|---|---|---|
| Bronze | Append-only + `_batch_id` | Preserve history |
| Silver | `INSERT ... ON CONFLICT DO UPDATE` | Handle reruns safely |
| Gold | `TRUNCATE + INSERT` (in transaction) | Always consistent |

---

## Files

```
pipelines/
├── bronze/
│   └── ingest_raw.py          # Raw file/API ingestion
├── silver/
│   └── clean_transform.py     # Cleaning, typing, upsert
├── gold/
│   └── aggregate_kpis.py      # KPI computations
└── idempotency/
    └── patterns.py            # 4 idempotency patterns explained
```

---

## Running Locally

```bash
# Run seed first (generates raw data)
python scripts/seed_data.py

# Then trigger the pipeline
docker compose exec airflow-webserver \
    airflow dags trigger medallion_pipeline
```

---

## Exercises

1. ⭐ Add a new column `is_high_value` to `silver.orders` (orders > $500)
2. ⭐⭐ Add a new KPI table `gold.category_revenue` (revenue by product category per month)
3. ⭐⭐⭐ Implement a watermark-based incremental Bronze → Silver load
