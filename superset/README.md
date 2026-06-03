# 📊 Superset — Stakeholder Dashboards

Apache Superset is a fully open-source BI platform. In this playground, it connects to the Gold layer and provides KPI dashboards for stakeholders.

---

## Accessing Superset

1. Open [http://localhost:8088](http://localhost:8088)
2. Login: `admin` / `admin`

---

## Connecting to the Warehouse

1. Go to **Settings → Database Connections → + Database**
2. Select **PostgreSQL**
3. Use this connection string:
   ```
   postgresql://playground:playground@postgres:5432/warehouse
   ```
4. Test & Save

---

## Building Your First Dashboard

### Step 1: Create a Dataset
- **Data → Datasets → + Dataset**
- Select `gold.daily_revenue`

### Step 2: Create a Chart
- **Charts → + Chart**
- Dataset: `daily_revenue`
- Chart type: **Line Chart**
- X-axis: `revenue_date`, Metric: `SUM(gross_revenue)`

### Step 3: Create a Dashboard
- **Dashboards → + Dashboard**
- Drag & drop your charts
- Add KPI scorecards for: Total Revenue, AOV, Unique Customers

---

## Recommended Charts for the Gold Layer

| Table | Chart Type | KPI |
|---|---|---|
| `gold.daily_revenue` | Line Chart | Daily revenue trend |
| `gold.monthly_revenue` | Bar Chart | Monthly revenue + MoM |
| `gold.customer_ltv` | Pie Chart | Customers by LTV segment |
| `gold.product_performance` | Table | Top products by revenue |
| `gold.customer_ltv` | Big Number | Total LTV |

---

## Exercises

1. ⭐ Build a "Revenue Overview" dashboard with 4 KPI tiles
2. ⭐⭐ Add a filter to slice revenue by customer tier
3. ⭐⭐ Build a "Product Performance" table with conditional formatting
