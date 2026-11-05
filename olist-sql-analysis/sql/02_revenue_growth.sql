-- Set 2: revenue and growth.
-- Revenue = sum of item prices (freight excluded) on delivered orders.
-- Trend window = Jan 2017 to Aug 2018, the only complete months in the data.

-- Q1. Monthly revenue, orders, average order value and month-over-month growth
WITH order_rev AS (
  SELECT o.order_id,
         strftime('%Y-%m', o.order_purchase_timestamp) AS month,
         SUM(i.price) AS revenue
  FROM orders o JOIN order_items i ON i.order_id = o.order_id
  WHERE o.order_status = 'delivered'
    AND o.order_purchase_timestamp >= '2017-01-01' AND o.order_purchase_timestamp < '2018-09-01'
  GROUP BY o.order_id
), monthly AS (
  SELECT month, COUNT(*) AS orders, SUM(revenue) AS revenue, AVG(revenue) AS aov
  FROM order_rev GROUP BY month
)
SELECT month, orders,
       ROUND(revenue, 0) AS revenue_brl,
       ROUND(aov, 2) AS avg_order_value,
       ROUND(100.0 * (revenue - LAG(revenue) OVER (ORDER BY month)) / LAG(revenue) OVER (ORDER BY month), 1) AS mom_growth_pct
FROM monthly
ORDER BY month;

-- Q2. Year-over-year: Jan-Aug 2018 vs Jan-Aug 2017
SELECT strftime('%Y', o.order_purchase_timestamp) AS year,
       COUNT(DISTINCT o.order_id) AS orders,
       ROUND(SUM(i.price), 0) AS revenue_brl,
       ROUND(SUM(i.price) / COUNT(DISTINCT o.order_id), 2) AS avg_order_value
FROM orders o JOIN order_items i ON i.order_id = o.order_id
WHERE o.order_status = 'delivered'
  AND strftime('%m', o.order_purchase_timestamp) BETWEEN '01' AND '08'
  AND o.order_purchase_timestamp >= '2017-01-01' AND o.order_purchase_timestamp < '2018-09-01'
GROUP BY year;

-- Q3. Top 10 categories by revenue, with share and running total
WITH cat AS (
  SELECT COALESCE(t.product_category_name_english, 'unknown') AS category,
         SUM(i.price) AS revenue
  FROM orders o
  JOIN order_items i ON i.order_id = o.order_id
  JOIN products p ON p.product_id = i.product_id
  LEFT JOIN category_translation t ON t.product_category_name = p.product_category_name
  WHERE o.order_status = 'delivered'
  GROUP BY category
)
SELECT category,
       ROUND(revenue, 0) AS revenue_brl,
       ROUND(100.0 * revenue / SUM(revenue) OVER (), 1) AS share_pct,
       ROUND(100.0 * SUM(revenue) OVER (ORDER BY revenue DESC) / SUM(revenue) OVER (), 1) AS cumulative_pct
FROM cat
ORDER BY revenue DESC
LIMIT 10;

-- Q4. Seller concentration (Pareto): how much revenue comes from the top 20% of sellers?
WITH seller_rev AS (
  SELECT i.seller_id, SUM(i.price) AS revenue
  FROM orders o JOIN order_items i ON i.order_id = o.order_id
  WHERE o.order_status = 'delivered'
  GROUP BY i.seller_id
), ranked AS (
  SELECT revenue, NTILE(5) OVER (ORDER BY revenue DESC) AS quintile FROM seller_rev
)
SELECT quintile,
       COUNT(*) AS sellers,
       ROUND(SUM(revenue), 0) AS revenue_brl,
       ROUND(100.0 * SUM(revenue) / (SELECT SUM(revenue) FROM seller_rev), 1) AS share_pct
FROM ranked
GROUP BY quintile
ORDER BY quintile;

-- Q5. Average order value and order count by main payment type
-- (an order can use several payments, so its largest payment sets the main type)
WITH main_pay AS (
  SELECT order_id, payment_type,
         ROW_NUMBER() OVER (PARTITION BY order_id ORDER BY payment_value DESC) AS rn
  FROM order_payments
), order_rev AS (
  SELECT i.order_id, SUM(i.price) AS revenue
  FROM order_items i JOIN orders o ON o.order_id = i.order_id
  WHERE o.order_status = 'delivered'
  GROUP BY i.order_id
)
SELECT m.payment_type,
       COUNT(*) AS orders,
       ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 1) AS order_share_pct,
       ROUND(AVG(r.revenue), 2) AS avg_order_value
FROM main_pay m JOIN order_rev r ON r.order_id = m.order_id
WHERE m.rn = 1
GROUP BY m.payment_type
ORDER BY orders DESC;

-- Q6. Revenue and average order value by customer state (top 10 by revenue)
SELECT c.customer_state AS state,
       COUNT(DISTINCT o.order_id) AS orders,
       ROUND(SUM(i.price), 0) AS revenue_brl,
       ROUND(100.0 * SUM(i.price) / SUM(SUM(i.price)) OVER (), 1) AS share_pct,
       ROUND(SUM(i.price) / COUNT(DISTINCT o.order_id), 2) AS avg_order_value
FROM orders o
JOIN order_items i ON i.order_id = o.order_id
JOIN customers c ON c.customer_id = o.customer_id
WHERE o.order_status = 'delivered'
GROUP BY c.customer_state
ORDER BY revenue_brl DESC
LIMIT 10;

-- Q7. Freight as a share of item price, by order-size band (does shipping eat small orders?)
WITH order_tot AS (
  SELECT i.order_id, SUM(i.price) AS items, SUM(i.freight_value) AS freight
  FROM order_items i JOIN orders o ON o.order_id = i.order_id
  WHERE o.order_status = 'delivered'
  GROUP BY i.order_id
)
SELECT CASE WHEN items < 50 THEN '1) under 50'
            WHEN items < 100 THEN '2) 50-100'
            WHEN items < 200 THEN '3) 100-200'
            ELSE '4) 200+' END AS order_value_band,
       COUNT(*) AS orders,
       ROUND(100.0 * SUM(freight) / SUM(items), 1) AS freight_pct_of_items
FROM order_tot
GROUP BY order_value_band
ORDER BY order_value_band;
