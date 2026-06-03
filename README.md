# data-pipelines-101
> A hands-on, self-contained learning playground for mastering moder Data Engineering concepts from raw ingestion to stakeholder-ready dashboards. 


# 🏗️ Data Engineering Playground

[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker&logoColor=white)](https://docs.docker.com/compose/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-336791?logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![Apache Airflow](https://img.shields.io/badge/Apache-Airflow-017CEE?logo=apacheairflow&logoColor=white)](https://airflow.apache.org/)
[![SQLMesh](https://img.shields.io/badge/SQLMesh-OSS-FF6B35)](https://sqlmesh.com/)
[![Apache Superset](https://img.shields.io/badge/Apache-Superset-20A7C9?logo=apache&logoColor=white)](https://superset.apache.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## 🎯 What You'll Learn

| Concept | Tool | Module |
|---|---|---|
| Pipeline design & idempotency | Python + Airflow | `pipelines/` |
| SQL fundamentals to advanced | PostgreSQL | `sql/` |
| Medallion Architecture | Python + SQLMesh | `bronze/silver/gold` |
| Workflow orchestration | Apache Airflow | `airflow/dags/` |
| dbt-style transformations | SQLMesh (open source) | `dbt_project/` |
| Stakeholder dashboards | Apache Superset | `superset/` |
| Data quality & testing | Great Expectations | `tests/` |

---

## 🏛️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    DATA ENGINEERING PLAYGROUND                   │
│                                                                   │
│  ┌──────────┐    ┌──────────────────────────────────────────┐   │
│  │  Source  │    │           Medallion Architecture          │   │
│  │  Data    │───▶│  🥉 Bronze  ──▶  🥈 Silver  ──▶  🥇 Gold │   │
│  │  (CSV /  │    │  (Raw)         (Cleaned)    (Aggregated)  │   │
│  │  API)    │    └──────────────────────┬───────────────────┘   │
│  └──────────┘                           │                        │
│                                         ▼                        │
│  ┌──────────┐    ┌──────────┐    ┌──────────────┐              │
│  │ Airflow  │    │ SQLMesh  │    │   Superset   │              │
│  │(Orchestr)│    │(Transfrm)│    │ (Dashboards) │              │
│  └──────────┘    └──────────┘    └──────────────┘              │
│                                                                   │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │              PostgreSQL + pgAdmin                        │    │
│  └─────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🛠️ Stack

| Service | Purpose | Port |
|---|---|---|
| **PostgreSQL 16** | Primary data warehouse | `5432` |
| **pgAdmin 4** | SQL IDE & DB explorer | `5050` |
| **Apache Airflow 2.8** | Pipeline orchestration | `8080` |
| **SQLMesh** | dbt-style SQL transforms (OSS) | CLI |
| **Apache Superset** | BI dashboards & KPI visuals | `8088` |

---

## 🚀 Quick Start

### Prerequisites
- [Docker Desktop](https://www.docker.com/products/docker-desktop/) ≥ 24.0
- [Git](https://git-scm.com/)
- 8 GB RAM recommended

### 1. Clone & Configure

```bash
git clone https://github.com/Numbersdontlie/data-pipelines-101.git
cd data-pipelines-101
cp .env.example .env
```

### 2. Launch the Stack

```bash
docker compose up -d
```

Wait ~2 minutes for all services to initialize and be ready.

### 3. Verify Services

```bash
docker compose ps
```

| Service | URL | Credentials |
|---|---|---|
| pgAdmin | http://localhost:5050 | admin@playground.dev / playground |
| Airflow | http://localhost:8080 | admin / admin |
| Superset | http://localhost:8088 | admin / admin |

### 4. Load Sample Data

```bash
docker compose exec airflow-webserver python /opt/airflow/scripts/seed_data.py
```

### 5. Run Your First Pipeline

```bash
# Trigger the full medallion pipeline in Airflow UI at localhost + assigned port
# Or run manually:
docker compose exec airflow-webserver airflow dags trigger medallion_pipeline
```

---

## 📚 Learning Modules

### Module 1 — SQL Fundamentals
📁 `sql/`

Start here if you're new to SQL. Covers:
- DDL: `CREATE`, `ALTER`, `DROP`
- DML: `INSERT`, `UPDATE`, `DELETE`, `UPSERT`
- Queries: JOINs, CTEs, Window Functions, Aggregations
- Advanced: Recursive CTEs, JSON, Array operations

```bash
# Connect to PostgreSQL
docker compose exec postgres psql -U playground -d warehouse
# Or open pgAdmin at http://localhost:5050
```

👉 See [`sql/README.md`](sql/README.md)

---

### Module 2 — Medallion Architecture
📁 `pipelines/`

Learn the industry-standard Bronze → Silver → Gold pattern:

```
Raw CSV/API  →  Bronze (exact copy)  →  Silver (cleaned)  →  Gold (business-ready)
```

| Layer | Description | Schema |
|---|---|---|
| 🥉 **Bronze** | Raw ingestion, no transformations | `bronze.*` |
| 🥈 **Silver** | Cleaned, typed, deduplicated | `silver.*` |
| 🥇 **Gold** | Aggregated KPIs, business logic | `gold.*` |

👉 See [`pipelines/README.md`](pipelines/README.md)

---

### Module 3 — Idempotent Pipelines
📁 `pipelines/idempotency/`

The most critical concept in production data engineering:

> **"Running a pipeline N times produces the same result as running it once."**

Learn patterns for:
- `TRUNCATE + INSERT` (full refresh)
- `INSERT ... ON CONFLICT DO UPDATE` (UPSERT)
- Partition-based incremental loads
- Watermark-based CDC

👉 See [`pipelines/README.md#idempotency`](pipelines/README.md#idempotency)

---

### Module 4 — Airflow Orchestration
📁 `airflow/dags/`

Learn DAG design with real pipelines:
- Task dependencies & XComs
- Sensors & triggers
- Backfill & catchup
- SLA monitoring
- Custom operators

👉 See [`airflow/README.md`](airflow/README.md)

---

### Module 5 — SQLMesh (dbt Alternative)
📁 `dbt_project/`

SQLMesh is a fully open-source SQL transformation framework. Learn:
- Model types: `VIEW`, `FULL`, `INCREMENTAL_BY_TIME_RANGE`
- Testing & auditing
- Lineage visualization
- CI/CD integration

```bash
# Run all models
docker compose exec sqlmesh sqlmesh run

# Preview changes
docker compose exec sqlmesh sqlmesh plan

# Run tests
docker compose exec sqlmesh sqlmesh test
```

👉 See [`dbt_project/README.md`](dbt_project/README.md)

---

### Module 6 — Superset Dashboards
📁 `superset/`

Build stakeholder-ready dashboards with Apache Superset:
- Connect to Gold layer tables
- Build KPI scorecards
- Create time-series charts
- Publish interactive dashboards

👉 See [`superset/README.md`](superset/README.md)

---

## 📊 Sample Dataset

This playground uses a synthetic **E-Commerce dataset** covering:

| Table | Rows | Description |
|---|---|---|
| `orders` | 50,000 | Order transactions |
| `customers` | 10,000 | Customer profiles |
| `products` | 500 | Product catalog |
| `order_items` | 150,000 | Line items per order |
| `events` | 500,000 | Clickstream / web events |

**KPIs computed in Gold layer:**
- Revenue by day / week / month
- Customer Lifetime Value (CLV)
- Average Order Value (AOV)
- Churn rate
- Top products by revenue

---

## 🗂️ Project Structure

```
data-engineering-playground/
│
├── 📄 README.md                    ← You are here
├── 📄 docker-compose.yml           ← Full stack definition
├── 📄 .env.example                 ← Environment variables template
│
├── 🐘 docker/                      ← Dockerfiles & configs
│   ├── postgres/
│   │   └── init.sql                ← DB init script
│   ├── airflow/
│   │   └── Dockerfile
│   └── superset/
│       └── superset_config.py
│
├── 🥉 pipelines/
│   ├── README.md
│   ├── bronze/
│   │   └── ingest_raw.py           ← Raw ingestion
│   ├── silver/
│   │   └── clean_transform.py      ← Cleaning & typing
│   ├── gold/
│   │   └── aggregate_kpis.py       ← Business aggregations
│   └── idempotency/
│       └── patterns.py             ← Idempotency examples
│
├── 🗄️ sql/
│   ├── README.md
│   ├── ddl/                        ← Schema definitions
│   ├── dml/                        ← Data manipulation
│   └── queries/                    ← Practice queries
│
├── ✈️ airflow/
│   ├── README.md
│   └── dags/
│       ├── medallion_pipeline.py   ← Full medallion DAG
│       ├── bronze_ingestion.py
│       ├── silver_transform.py
│       └── gold_aggregation.py
│
├── 🔄 dbt_project/                 ← SQLMesh project
│   ├── README.md
│   ├── config.py
│   ├── models/
│   │   ├── bronze/
│   │   ├── silver/
│   │   └── gold/
│   ├── tests/
│   └── macros/
│
├── 📊 superset/
│   ├── README.md
│   └── dashboards/                 ← Exported dashboard JSONs
│
├── 📁 data/
│   └── raw/                        ← Sample CSV seed files
│
└── 🔧 scripts/
    ├── seed_data.py                ← Generate sample data
    └── reset.sh                    ← Reset all services
```

---

## 🧪 Exercises

Each module includes guided exercises with solutions:

| # | Exercise | Difficulty | Module |
|---|---|---|---|
| 1 | Write an idempotent UPSERT for orders | ⭐ Easy | SQL |
| 2 | Build a Bronze ingestion pipeline | ⭐⭐ Medium | Pipelines |
| 3 | Clean & deduplicate customers in Silver | ⭐⭐ Medium | Pipelines |
| 4 | Compute Monthly Revenue in Gold | ⭐⭐ Medium | SQL / SQLMesh |
| 5 | Create an Airflow DAG with retries | ⭐⭐⭐ Hard | Airflow |
| 6 | Build a Revenue KPI dashboard | ⭐⭐ Medium | Superset |
| 7 | Write a SQLMesh incremental model | ⭐⭐⭐ Hard | SQLMesh |
| 8 | Implement watermark-based CDC | ⭐⭐⭐ Hard | Pipelines |

---

## 🤝 Contributing

Contributions are welcome! See [`CONTRIBUTING.md`](CONTRIBUTING.md) for guidelines.

---

## 📜 License

MIT — free to use, fork, and learn from.

---

<p align="center">
  Built for learners. Inspired by production. 🚀
</p>
