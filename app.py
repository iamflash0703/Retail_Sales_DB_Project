"""
Retail Sales Analytics — Streamlit dashboard on top of the SQL project.

Run locally:
    pip install streamlit pandas
    streamlit run app.py

Deploy the same way as your other projects (Streamlit Community Cloud,
or Render as a web service with `streamlit run app.py --server.port $PORT
--server.address 0.0.0.0`).
"""

import sqlite3
import pandas as pd
import streamlit as st

st.set_page_config(page_title="Retail Sales Analytics", layout="wide")

DB_PATH = "retail.db"


@st.cache_resource
def get_connection():
    return sqlite3.connect(DB_PATH, check_same_thread=False)


def run_query(sql: str) -> pd.DataFrame:
    return pd.read_sql_query(sql, get_connection())


st.title("📊 Retail Sales Analytics")
st.caption(
    "A small e-commerce dataset (400 customers, ~1,000 orders) queried live with SQL — "
    "joins, CTEs, window functions, and RFM segmentation."
)

tab1, tab2, tab3, tab4 = st.tabs(
    ["Revenue Trends", "Products & Categories", "Customer Segments (RFM)", "Cohort Retention"]
)

# ---------------- Tab 1: Revenue trends ----------------
with tab1:
    st.subheader("Monthly Revenue & Cumulative Growth")

    monthly_sql = """
        WITH monthly AS (
            SELECT
                strftime('%Y-%m', o.order_date) AS month,
                SUM(oi.quantity * oi.unit_price) AS revenue,
                COUNT(DISTINCT o.order_id) AS orders
            FROM orders o
            JOIN order_items oi ON oi.order_id = o.order_id
            WHERE o.status = 'completed'
            GROUP BY month
        )
        SELECT
            month,
            revenue,
            orders,
            SUM(revenue) OVER (ORDER BY month) AS cumulative_revenue,
            revenue - LAG(revenue) OVER (ORDER BY month) AS change_vs_prev_month
        FROM monthly
        ORDER BY month;
    """
    df_monthly = run_query(monthly_sql)

    col1, col2 = st.columns(2)
    with col1:
        st.line_chart(df_monthly.set_index("month")["revenue"], height=300)
        st.caption("Monthly revenue")
    with col2:
        st.line_chart(df_monthly.set_index("month")["cumulative_revenue"], height=300)
        st.caption("Cumulative revenue (running total)")

    st.dataframe(df_monthly, use_container_width=True)

    st.subheader("Order Status Breakdown")
    status_sql = """
        SELECT status, COUNT(*) AS order_count,
               ROUND(100.0 * COUNT(*) / (SELECT COUNT(*) FROM orders), 2) AS pct_of_all_orders
        FROM orders
        GROUP BY status
        ORDER BY order_count DESC;
    """
    st.dataframe(run_query(status_sql), use_container_width=True)

# ---------------- Tab 2: Products & categories ----------------
with tab2:
    st.subheader("Top Products by Revenue")
    top_products_sql = """
        SELECT p.product_name, p.category,
               SUM(oi.quantity) AS units_sold,
               ROUND(SUM(oi.quantity * oi.unit_price), 2) AS revenue
        FROM order_items oi
        JOIN orders o ON o.order_id = oi.order_id
        JOIN products p ON p.product_id = oi.product_id
        WHERE o.status = 'completed'
        GROUP BY p.product_id
        ORDER BY revenue DESC
        LIMIT 10;
    """
    df_top = run_query(top_products_sql)
    st.bar_chart(df_top.set_index("product_name")["revenue"], height=350)
    st.dataframe(df_top, use_container_width=True)

    st.subheader("Revenue Share by Category")
    category_sql = """
        SELECT p.category,
               ROUND(SUM(oi.quantity * oi.unit_price), 2) AS category_revenue,
               ROUND(100.0 * SUM(oi.quantity * oi.unit_price) /
                     (SELECT SUM(oi2.quantity * oi2.unit_price)
                      FROM order_items oi2
                      JOIN orders o2 ON o2.order_id = oi2.order_id
                      WHERE o2.status = 'completed'), 2) AS pct_of_total_revenue
        FROM order_items oi
        JOIN orders o ON o.order_id = oi.order_id
        JOIN products p ON p.product_id = oi.product_id
        WHERE o.status = 'completed'
        GROUP BY p.category
        ORDER BY category_revenue DESC;
    """
    df_cat = run_query(category_sql)
    col1, col2 = st.columns([1, 1])
    with col1:
        st.dataframe(df_cat, use_container_width=True)
    with col2:
        st.bar_chart(df_cat.set_index("category")["pct_of_total_revenue"], height=300)

# ---------------- Tab 3: RFM segmentation ----------------
with tab3:
    st.subheader("Customer Segments (Recency, Frequency, Monetary)")
    st.caption(
        "Segments customers using NTILE() quartiles on recency, order frequency, "
        "and total spend — a standard technique for prioritizing retention/marketing effort."
    )

    rfm_sql = """
        WITH last_order AS (
            SELECT customer_id, MAX(order_date) AS last_order_date
            FROM orders WHERE status = 'completed'
            GROUP BY customer_id
        ),
        rfm_base AS (
            SELECT
                c.customer_id, c.customer_name,
                CAST(julianday((SELECT MAX(order_date) FROM orders)) - julianday(lo.last_order_date) AS INTEGER) AS recency_days,
                COUNT(DISTINCT o.order_id) AS frequency,
                SUM(oi.quantity * oi.unit_price) AS monetary
            FROM customers c
            JOIN last_order lo ON lo.customer_id = c.customer_id
            JOIN orders o ON o.customer_id = c.customer_id AND o.status = 'completed'
            JOIN order_items oi ON oi.order_id = o.order_id
            GROUP BY c.customer_id
        ),
        rfm_scored AS (
            SELECT *,
                NTILE(4) OVER (ORDER BY recency_days DESC) AS r_score,
                NTILE(4) OVER (ORDER BY frequency ASC) AS f_score,
                NTILE(4) OVER (ORDER BY monetary ASC) AS m_score
            FROM rfm_base
        )
        SELECT customer_name, recency_days, frequency, ROUND(monetary, 2) AS monetary,
            r_score, f_score, m_score,
            CASE
                WHEN r_score >= 3 AND f_score >= 3 AND m_score >= 3 THEN 'Champion'
                WHEN r_score >= 3 AND f_score < 3 THEN 'Promising / New'
                WHEN r_score < 2 AND f_score >= 3 THEN 'At Risk (was loyal)'
                WHEN r_score < 2 AND f_score < 2 THEN 'Lost'
                ELSE 'Needs Attention'
            END AS segment
        FROM rfm_scored
        ORDER BY monetary DESC;
    """
    df_rfm = run_query(rfm_sql)

    seg_counts = df_rfm["segment"].value_counts().reset_index()
    seg_counts.columns = ["segment", "customers"]
    col1, col2 = st.columns([1, 2])
    with col1:
        st.dataframe(seg_counts, use_container_width=True)
    with col2:
        st.bar_chart(seg_counts.set_index("segment")["customers"], height=300)

    st.dataframe(df_rfm, use_container_width=True)

# ---------------- Tab 4: Cohort retention ----------------
with tab4:
    st.subheader("Cohort Retention Heatmap Data")
    st.caption(
        "Of customers who signed up in a given month, what % placed an order "
        "in each month afterward? Classic cohort-retention view."
    )

    cohort_sql = """
        WITH cohorts AS (
            SELECT customer_id, strftime('%Y-%m', signup_date) AS cohort_month
            FROM customers
        ),
        customer_orders AS (
            SELECT DISTINCT customer_id, strftime('%Y-%m', order_date) AS order_month
            FROM orders WHERE status = 'completed'
        )
        SELECT ch.cohort_month, co.order_month,
               COUNT(DISTINCT co.customer_id) AS active_customers,
               (SELECT COUNT(*) FROM cohorts WHERE cohort_month = ch.cohort_month) AS cohort_size,
               ROUND(100.0 * COUNT(DISTINCT co.customer_id) /
                     (SELECT COUNT(*) FROM cohorts WHERE cohort_month = ch.cohort_month), 2) AS pct_active
        FROM cohorts ch
        JOIN customer_orders co ON co.customer_id = ch.customer_id
        WHERE co.order_month >= ch.cohort_month
        GROUP BY ch.cohort_month, co.order_month
        ORDER BY ch.cohort_month, co.order_month;
    """
    df_cohort = run_query(cohort_sql)
    pivot = df_cohort.pivot(index="cohort_month", columns="order_month", values="pct_active")
    st.dataframe(pivot.style.background_gradient(cmap="Greens", axis=None).format(precision=1), use_container_width=True)
