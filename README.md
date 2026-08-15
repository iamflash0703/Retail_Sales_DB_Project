# Retail Sales Analytics (SQL)

A SQL project where I practiced writing real analytical queries — joins, CTEs, and window functions — on a small e-commerce dataset, and built a Streamlit dashboard on top of it.

🔗 **Live app:** https://xqjmnwqxgqer62qhmrljjb.streamlit.app/

## What it does

The dataset has 4 tables — customers, products, orders, and order_items — with about 400 customers and 1,000 orders. Using this data, the project answers questions like:

- What's the monthly revenue trend?
- Which products/categories sell the most?
- What % of customers come back for a second order?
- Who are the top customers per state?
- Which customers are "Champions" vs "At Risk" (RFM segmentation)?
- How well do we retain customers month over month (cohort analysis)?

All of this is queried live and shown in the dashboard.

## Tech stack

- **SQLite** for the database
- **Python (pandas)** to generate the sample data
- **Streamlit** for the dashboard

## Files

- `schema.sql` — table definitions
- `generate_data.py` — creates the sample data
- `queries.sql` — all the SQL queries used in the project
- `app.py` — the Streamlit dashboard
- `retail.db` — the SQLite database

## How to run it locally

```bash
pip install streamlit pandas matplotlib
python generate_data.py
streamlit run app.py
```

## What I learned

This was mainly practice for writing SQL beyond basic SELECT/WHERE — things like CTEs, `RANK()`, `LAG()`, and `NTILE()` for RFM segmentation, which I hadn't used before this project.
