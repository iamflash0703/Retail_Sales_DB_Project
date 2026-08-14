-- ============================================================
-- Retail Sales Analytics — Queries
-- Run with: sqlite3 retail.db < queries.sql
-- Each query answers a real business question, not just a
-- syntax demo. Grouped roughly easy -> advanced.
-- ============================================================

-- 1) Monthly revenue trend (completed orders only)
-- Business question: is revenue growing month over month?
SELECT
    strftime('%Y-%m', o.order_date) AS month,
    ROUND(SUM(oi.quantity * oi.unit_price), 2) AS revenue,
    COUNT(DISTINCT o.order_id) AS orders
FROM orders o
JOIN order_items oi ON oi.order_id = o.order_id
WHERE o.status = 'completed'
GROUP BY month
ORDER BY month;


-- 2) Top 10 products by revenue
-- Business question: which products should we double down on inventory for?
SELECT
    p.product_name,
    p.category,
    SUM(oi.quantity) AS units_sold,
    ROUND(SUM(oi.quantity * oi.unit_price), 2) AS revenue
FROM order_items oi
JOIN orders o ON o.order_id = oi.order_id
JOIN products p ON p.product_id = oi.product_id
WHERE o.status = 'completed'
GROUP BY p.product_id
ORDER BY revenue DESC
LIMIT 10;


-- 3) Revenue by category, with each category's % share of total revenue
-- Demonstrates: subquery for grand total, arithmetic in SELECT
SELECT
    p.category,
    ROUND(SUM(oi.quantity * oi.unit_price), 2) AS category_revenue,
    ROUND(
        100.0 * SUM(oi.quantity * oi.unit_price) /
        (SELECT SUM(oi2.quantity * oi2.unit_price)
         FROM order_items oi2
         JOIN orders o2 ON o2.order_id = oi2.order_id
         WHERE o2.status = 'completed'),
        2
    ) AS pct_of_total_revenue
FROM order_items oi
JOIN orders o ON o.order_id = oi.order_id
JOIN products p ON p.product_id = oi.product_id
WHERE o.status = 'completed'
GROUP BY p.category
ORDER BY category_revenue DESC;


-- 4) Order status breakdown (cancellation / return rate)
-- Business question: what % of orders are we losing to cancellations/returns?
SELECT
    status,
    COUNT(*) AS order_count,
    ROUND(100.0 * COUNT(*) / (SELECT COUNT(*) FROM orders), 2) AS pct_of_all_orders
FROM orders
GROUP BY status
ORDER BY order_count DESC;


-- 5) Repeat purchase rate
-- Business question: what share of customers come back for a 2nd order?
-- Demonstrates: CTE + conditional aggregation
WITH order_counts AS (
    SELECT customer_id, COUNT(*) AS n_orders
    FROM orders
    GROUP BY customer_id
)
SELECT
    COUNT(*) AS total_customers,
    SUM(CASE WHEN n_orders > 1 THEN 1 ELSE 0 END) AS repeat_customers,
    ROUND(100.0 * SUM(CASE WHEN n_orders > 1 THEN 1 ELSE 0 END) / COUNT(*), 2) AS repeat_rate_pct
FROM order_counts;


-- 6) Running total of monthly revenue (cumulative revenue over time)
-- Demonstrates: window function SUM() OVER (ORDER BY ...)
WITH monthly AS (
    SELECT
        strftime('%Y-%m', o.order_date) AS month,
        SUM(oi.quantity * oi.unit_price) AS revenue
    FROM orders o
    JOIN order_items oi ON oi.order_id = o.order_id
    WHERE o.status = 'completed'
    GROUP BY month
)
SELECT
    month,
    ROUND(revenue, 2) AS revenue,
    ROUND(SUM(revenue) OVER (ORDER BY month), 2) AS cumulative_revenue
FROM monthly
ORDER BY month;


-- 7) Rank customers by lifetime spend within their state (top 3 per state)
-- Demonstrates: window function RANK() OVER (PARTITION BY ... ORDER BY ...)
-- Note: SQLite has no QUALIFY clause, so the rank filter is applied by
-- wrapping the windowed query in an outer SELECT instead.
WITH customer_spend AS (
    SELECT
        c.customer_id,
        c.customer_name,
        c.state,
        SUM(oi.quantity * oi.unit_price) AS lifetime_spend
    FROM customers c
    JOIN orders o ON o.customer_id = c.customer_id
    JOIN order_items oi ON oi.order_id = o.order_id
    WHERE o.status = 'completed'
    GROUP BY c.customer_id
),
ranked AS (
    SELECT
        state,
        customer_name,
        ROUND(lifetime_spend, 2) AS lifetime_spend,
        RANK() OVER (PARTITION BY state ORDER BY lifetime_spend DESC) AS rank_in_state
    FROM customer_spend
)
SELECT * FROM ranked
WHERE rank_in_state <= 3
ORDER BY state, rank_in_state;


-- 8) Month-over-month revenue growth %
-- Demonstrates: window function LAG() for period-over-period comparison
WITH monthly AS (
    SELECT
        strftime('%Y-%m', o.order_date) AS month,
        SUM(oi.quantity * oi.unit_price) AS revenue
    FROM orders o
    JOIN order_items oi ON oi.order_id = o.order_id
    WHERE o.status = 'completed'
    GROUP BY month
)
SELECT
    month,
    ROUND(revenue, 2) AS revenue,
    ROUND(revenue - LAG(revenue) OVER (ORDER BY month), 2) AS change_vs_prev_month,
    ROUND(
        100.0 * (revenue - LAG(revenue) OVER (ORDER BY month)) / LAG(revenue) OVER (ORDER BY month),
        2
    ) AS pct_change_vs_prev_month
FROM monthly
ORDER BY month;


-- 9) RFM segmentation (Recency, Frequency, Monetary)
-- Business question: who are our best/at-risk customers?
-- Demonstrates: multi-CTE pipeline, NTILE() window function, CASE-based segmentation
WITH last_order AS (
    SELECT customer_id, MAX(order_date) AS last_order_date
    FROM orders
    WHERE status = 'completed'
    GROUP BY customer_id
),
rfm_base AS (
    SELECT
        c.customer_id,
        c.customer_name,
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
    SELECT
        *,
        NTILE(4) OVER (ORDER BY recency_days DESC) AS r_score,   -- 4 = most recent
        NTILE(4) OVER (ORDER BY frequency ASC) AS f_score,       -- 4 = most frequent
        NTILE(4) OVER (ORDER BY monetary ASC) AS m_score         -- 4 = highest spend
    FROM rfm_base
)
SELECT
    customer_name,
    recency_days,
    frequency,
    ROUND(monetary, 2) AS monetary,
    r_score, f_score, m_score,
    CASE
        WHEN r_score >= 3 AND f_score >= 3 AND m_score >= 3 THEN 'Champion'
        WHEN r_score >= 3 AND f_score < 3 THEN 'Promising / New'
        WHEN r_score < 2 AND f_score >= 3 THEN 'At Risk (was loyal)'
        WHEN r_score < 2 AND f_score < 2 THEN 'Lost'
        ELSE 'Needs Attention'
    END AS segment
FROM rfm_scored
ORDER BY monetary DESC
LIMIT 25;


-- 10) Cohort retention: of customers who signed up in a given month,
-- what % placed at least one order in each subsequent month?
-- Demonstrates: cohort-style analysis, common in real analyst interviews
WITH cohorts AS (
    SELECT
        customer_id,
        strftime('%Y-%m', signup_date) AS cohort_month
    FROM customers
),
customer_orders AS (
    SELECT DISTINCT
        customer_id,
        strftime('%Y-%m', order_date) AS order_month
    FROM orders
    WHERE status = 'completed'
)
SELECT
    ch.cohort_month,
    co.order_month,
    COUNT(DISTINCT co.customer_id) AS active_customers,
    (SELECT COUNT(*) FROM cohorts WHERE cohort_month = ch.cohort_month) AS cohort_size,
    ROUND(
        100.0 * COUNT(DISTINCT co.customer_id) /
        (SELECT COUNT(*) FROM cohorts WHERE cohort_month = ch.cohort_month),
        2
    ) AS pct_active
FROM cohorts ch
JOIN customer_orders co ON co.customer_id = ch.customer_id
WHERE co.order_month >= ch.cohort_month
GROUP BY ch.cohort_month, co.order_month
ORDER BY ch.cohort_month, co.order_month;
