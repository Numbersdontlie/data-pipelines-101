# ✈️ Airflow — Pipeline Orchestration

Apache Airflow is the industry-standard workflow orchestration tool. In this playground, it schedules and monitors the full Medallion pipeline.

---

## Accessing Airflow

1. Open [http://localhost:8080](http://localhost:8080)
2. Login: `admin` / `admin`
3. Enable the `medallion_pipeline` DAG

---

## DAGs in This Playground

| DAG | Schedule | Description |
|---|---|---|
| `medallion_pipeline` | Daily 06:00 UTC | Full Bronze → Silver → Gold |

---

## Key Airflow Concepts

### DAG (Directed Acyclic Graph)
A DAG defines the pipeline: tasks and their dependencies. Each DAG has a schedule and a start date.

### Task Dependencies

```python
start >> bronze_validate
bronze_validate >> [silver_customers, silver_products]  # parallel!
[silver_customers, silver_products] >> silver_orders
silver_orders >> silver_order_items
silver_order_items >> [gold_revenue, gold_ltv, gold_products]
```

### Connections
Airflow stores DB credentials as **Connections**. The pipeline uses `postgres_playground`.

Set it up in the UI:
- **Admin → Connections → +**
- Conn ID: `postgres_playground`
- Conn Type: `Postgres`
- Host: `postgres`, Port: `5432`
- Login: `playground`, Password: `playground`
- Schema: `warehouse`

### Backfill
Re-run historical dates:
```bash
airflow dags backfill medallion_pipeline \
    --start-date 2024-01-01 \
    --end-date 2024-01-31
```

---

## Exercises

1. ⭐ Add a task that sends a Slack notification on pipeline success
2. ⭐⭐ Add a `data_quality_check` task between Silver and Gold
3. ⭐⭐⭐ Modify the DAG to use `execution_date` for incremental loads
