-- Data quality checks before any analysis.

-- 1. Order status mix
SELECT order_status, COUNT(*) AS orders
FROM orders
GROUP BY order_status
ORDER BY orders DESC;

-- 2. Date range of purchases, by month (spot partial months at the edges)
SELECT strftime('%Y-%m', order_purchase_timestamp) AS month, COUNT(*) AS orders
FROM orders
GROUP BY month
ORDER BY month;

-- 3. Delivered orders missing a delivery date, and non-delivered orders that have one
SELECT
  SUM(order_status = 'delivered' AND order_delivered_customer_date IS NULL) AS delivered_no_date,
  SUM(order_status <> 'delivered' AND order_delivered_customer_date IS NOT NULL) AS not_delivered_with_date
FROM orders;

-- 4. Duplicate keys
SELECT COUNT(*) - COUNT(DISTINCT order_id) AS dup_orders FROM orders;
SELECT COUNT(*) - COUNT(DISTINCT customer_id) AS dup_customer_ids FROM customers;

-- 5. Orders with no items, and items with no matching order
SELECT COUNT(*) AS orders_without_items
FROM orders o LEFT JOIN order_items i ON i.order_id = o.order_id
WHERE i.order_id IS NULL;

-- 6. Reviews: several reviews per order?
SELECT COUNT(*) - COUNT(DISTINCT order_id) AS extra_reviews FROM order_reviews;

-- 7. Products with no category, and categories missing a translation
SELECT COUNT(*) AS products_no_category FROM products WHERE product_category_name IS NULL;
SELECT COUNT(DISTINCT p.product_category_name) AS categories_no_translation
FROM products p LEFT JOIN category_translation t ON t.product_category_name = p.product_category_name
WHERE p.product_category_name IS NOT NULL AND t.product_category_name IS NULL;

-- 8. Payment total vs item total per order (do they reconcile?)
WITH item_tot AS (
  SELECT order_id, SUM(price + freight_value) AS items FROM order_items GROUP BY order_id
), pay_tot AS (
  SELECT order_id, SUM(payment_value) AS paid FROM order_payments GROUP BY order_id
)
SELECT COUNT(*) AS orders_compared,
       SUM(ABS(items - paid) > 1) AS off_by_more_than_1
FROM item_tot JOIN pay_tot USING (order_id);
