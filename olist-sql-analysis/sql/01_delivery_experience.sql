-- Set 1: delivery performance and customer experience.
-- Scope: delivered orders that have both a delivery date and an estimated date.
-- "Late" = delivered after the estimated delivery date shown to the customer.

-- Q1. Overall delivery performance
SELECT
  COUNT(*) AS delivered_orders,
  ROUND(AVG(julianday(order_delivered_customer_date) - julianday(order_purchase_timestamp)), 1) AS avg_days_to_deliver,
  ROUND(AVG(julianday(order_estimated_delivery_date) - julianday(order_purchase_timestamp)), 1) AS avg_days_promised,
  ROUND(100.0 * AVG(order_delivered_customer_date > order_estimated_delivery_date), 1) AS pct_late
FROM orders
WHERE order_status = 'delivered'
  AND order_delivered_customer_date IS NOT NULL;

-- Q2. Does late delivery hurt review scores? (one review per order: the most recent)
WITH latest_review AS (
  SELECT order_id, review_score,
         ROW_NUMBER() OVER (PARTITION BY order_id ORDER BY review_answer_timestamp DESC) AS rn
  FROM order_reviews
), d AS (
  SELECT o.order_id,
         CASE WHEN o.order_delivered_customer_date > o.order_estimated_delivery_date
              THEN 'late' ELSE 'on time' END AS delivery,
         r.review_score
  FROM orders o
  JOIN latest_review r ON r.order_id = o.order_id AND r.rn = 1
  WHERE o.order_status = 'delivered' AND o.order_delivered_customer_date IS NOT NULL
)
SELECT delivery,
       COUNT(*) AS orders,
       ROUND(AVG(review_score), 2) AS avg_score,
       ROUND(100.0 * AVG(review_score <= 2), 1) AS pct_1_2_stars,
       ROUND(100.0 * AVG(review_score = 5), 1) AS pct_5_stars
FROM d
GROUP BY delivery;

-- Q3. Review score by how many days late (the dose-response view)
WITH latest_review AS (
  SELECT order_id, review_score,
         ROW_NUMBER() OVER (PARTITION BY order_id ORDER BY review_answer_timestamp DESC) AS rn
  FROM order_reviews
), d AS (
  SELECT r.review_score,
         julianday(o.order_delivered_customer_date) - julianday(o.order_estimated_delivery_date) AS days_vs_estimate
  FROM orders o
  JOIN latest_review r ON r.order_id = o.order_id AND r.rn = 1
  WHERE o.order_status = 'delivered' AND o.order_delivered_customer_date IS NOT NULL
)
SELECT CASE
         WHEN days_vs_estimate <= -7 THEN '1) 7+ days early'
         WHEN days_vs_estimate <= 0  THEN '2) 0-7 days early'
         WHEN days_vs_estimate <= 3  THEN '3) 1-3 days late'
         WHEN days_vs_estimate <= 7  THEN '4) 4-7 days late'
         ELSE '5) 8+ days late' END AS delivery_bucket,
       COUNT(*) AS orders,
       ROUND(AVG(review_score), 2) AS avg_score,
       ROUND(100.0 * AVG(review_score <= 2), 1) AS pct_1_2_stars
FROM d
GROUP BY delivery_bucket
ORDER BY delivery_bucket;

-- Q4. Late-delivery rate by customer state (states with 1,000+ delivered orders)
SELECT c.customer_state AS state,
       COUNT(*) AS orders,
       ROUND(AVG(julianday(o.order_delivered_customer_date) - julianday(o.order_purchase_timestamp)), 1) AS avg_days_to_deliver,
       ROUND(100.0 * AVG(o.order_delivered_customer_date > o.order_estimated_delivery_date), 1) AS pct_late
FROM orders o
JOIN customers c ON c.customer_id = o.customer_id
WHERE o.order_status = 'delivered' AND o.order_delivered_customer_date IS NOT NULL
GROUP BY c.customer_state
HAVING COUNT(*) >= 1000
ORDER BY pct_late DESC;

-- Q5. Product categories with the worst late rate (500+ delivered orders)
-- DISTINCT order/category pairs so a multi-item order counts once per category.
WITH oc AS (
  SELECT DISTINCT o.order_id, t.product_category_name_english AS category,
         o.order_delivered_customer_date > o.order_estimated_delivery_date AS is_late,
         julianday(o.order_delivered_customer_date) - julianday(o.order_purchase_timestamp) AS days
  FROM orders o
  JOIN order_items i ON i.order_id = o.order_id
  JOIN products p ON p.product_id = i.product_id
  JOIN category_translation t ON t.product_category_name = p.product_category_name
  WHERE o.order_status = 'delivered' AND o.order_delivered_customer_date IS NOT NULL
)
SELECT category,
       COUNT(*) AS orders,
       ROUND(AVG(days), 1) AS avg_days_to_deliver,
       ROUND(100.0 * AVG(is_late), 1) AS pct_late
FROM oc
GROUP BY category
HAVING COUNT(*) >= 500
ORDER BY pct_late DESC
LIMIT 10;

-- Q6. Sellers with the worst late rate (50+ delivered orders), and how much they sell
WITH so AS (
  SELECT DISTINCT i.seller_id, o.order_id,
         o.order_delivered_customer_date > o.order_estimated_delivery_date AS is_late
  FROM orders o
  JOIN order_items i ON i.order_id = o.order_id
  WHERE o.order_status = 'delivered' AND o.order_delivered_customer_date IS NOT NULL
)
SELECT s.seller_id, s.seller_state AS state,
       COUNT(*) AS orders,
       ROUND(100.0 * AVG(is_late), 1) AS pct_late
FROM so JOIN sellers s ON s.seller_id = so.seller_id
GROUP BY s.seller_id
HAVING COUNT(*) >= 50
ORDER BY pct_late DESC
LIMIT 10;

-- Q7. Where do the late orders come from? Same-state vs cross-state shipping
WITH one_seller AS (
  -- keep orders served by exactly one seller so "same state" is unambiguous
  SELECT order_id, MIN(seller_id) AS seller_id
  FROM order_items GROUP BY order_id HAVING COUNT(DISTINCT seller_id) = 1
)
SELECT CASE WHEN c.customer_state = s.seller_state THEN 'same state' ELSE 'different state' END AS route,
       COUNT(*) AS orders,
       ROUND(AVG(julianday(o.order_delivered_customer_date) - julianday(o.order_purchase_timestamp)), 1) AS avg_days_to_deliver,
       ROUND(100.0 * AVG(o.order_delivered_customer_date > o.order_estimated_delivery_date), 1) AS pct_late
FROM orders o
JOIN one_seller os ON os.order_id = o.order_id
JOIN sellers s ON s.seller_id = os.seller_id
JOIN customers c ON c.customer_id = o.customer_id
WHERE o.order_status = 'delivered' AND o.order_delivered_customer_date IS NOT NULL
GROUP BY route;
