# Retail Sales Analytics (SQL)

A small end-to-end SQL analytics project on a synthetic e-commerce dataset:
400 customers, 20 products, ~1,000 orders, ~2,600 order line items across a
2-year window with realistic seasonality and repeat-purchase patterns.

**Live demo:** _add your deployed Streamlit link here after deploying_
**Stack:** SQLite · Python (pandas) · Streamlit

## What this project demonstrates

- **Multi-table joins** across customers → orders → order_items → products
- **CTEs (WITH clauses)**, including multi-step CTE pipelines
- **Window functions**: `SUM() OVER`, `RANK() OVER (PARTITION BY ...)`,
  `LAG() OVER`, `NTILE()`
- **RFM customer segmentation** (Recency, Frequency, Monetary) — a real
  technique used in marketing/growth analytics, not a toy query
- **Cohort retention analysis** — signup-month cohorts tracked across
  subsequent months, the same shape of query interviewers ask for at
  analytics-firm/product-company screens
- Correlated subqueries (e.g. % of total revenue per category)

## Project structure

```
sql-retail-analytics/
├── schema.sql          # table definitions (customers, products, orders, order_items)
├── generate_data.py     # generates realistic synthetic data, loads it into retail.db
├── queries.sql          # 10 standalone analytical queries, easy → advanced
├── app.py               # Streamlit dashboard built on top of the same queries
├── retail.db             # generated SQLite database (created by generate_data.py)
└── README.md
```

## How to run

```bash
# 1. Generate the database
python generate_data.py

# 2. Run the raw SQL queries (any SQLite client works, e.g.:)
sqlite3 retail.db < queries.sql

# 3. Or launch the interactive dashboard
pip install streamlit pandas
streamlit run app.py
```

## Sample findings from the generated dataset

- Electronics is the top revenue category (~44% of total revenue)
- ~47% of customers place more than one order (repeat purchase rate)
- Revenue shows clear festive-season seasonality (Oct–Nov peak)
- RFM segmentation surfaces a small "Champion" segment with 10+ orders
  and recent activity — the customers worth prioritizing for retention

## Why I built this

Built to demonstrate practical SQL beyond `SELECT * WHERE` — the kind of
query work (segmentation, cohort analysis, running totals) that comes up
in real data analyst/data scientist screens. Paired with a Streamlit
dashboard to keep the "ship it, don't just notebook it" pattern from my
other projects.

## Resume bullet (suggested)

> **Retail Sales Analytics (SQL)** — Designed a normalized 4-table schema
> and generated a realistic 2-year synthetic dataset (400 customers, ~1,000
> orders); wrote 10 analytical SQL queries using CTEs and window functions
> (RANK, LAG, NTILE) including RFM customer segmentation and cohort
> retention analysis; built an interactive Streamlit dashboard on top of
> the same query layer.
