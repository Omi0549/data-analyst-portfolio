"""Export one flat, order-level CSV for the Tableau dashboard.

Run after build_db.py:  python export_for_tableau.py
Output: tableau/olist_orders_for_tableau.csv  (one row per delivered order, Jan 2017 - Aug 2018)
"""
import sqlite3
from pathlib import Path

import pandas as pd

HERE = Path(__file__).parent
OUT = HERE / "tableau"
OUT.mkdir(exist_ok=True)

STATE_NAMES = {
    "AC": "Acre", "AL": "Alagoas", "AP": "Amapá", "AM": "Amazonas", "BA": "Bahia", "CE": "Ceará",
    "DF": "Distrito Federal", "ES": "Espírito Santo", "GO": "Goiás", "MA": "Maranhão",
    "MT": "Mato Grosso", "MS": "Mato Grosso do Sul", "MG": "Minas Gerais", "PA": "Pará",
    "PB": "Paraíba", "PR": "Paraná", "PE": "Pernambuco", "PI": "Piauí", "RJ": "Rio de Janeiro",
    "RN": "Rio Grande do Norte", "RS": "Rio Grande do Sul", "RO": "Rondônia", "RR": "Roraima",
    "SC": "Santa Catarina", "SP": "São Paulo", "SE": "Sergipe", "TO": "Tocantins",
}

QUERY = """
WITH latest_review AS (
  SELECT order_id, review_score,
         ROW_NUMBER() OVER (PARTITION BY order_id ORDER BY review_answer_timestamp DESC) AS rn
  FROM order_reviews
), order_money AS (
  SELECT order_id, SUM(price) AS revenue, SUM(freight_value) AS freight, COUNT(*) AS items
  FROM order_items GROUP BY order_id
), main_category AS (
  -- the category of the most expensive item in the order
  SELECT i.order_id, COALESCE(t.product_category_name_english, 'unknown') AS category,
         ROW_NUMBER() OVER (PARTITION BY i.order_id ORDER BY i.price DESC) AS rn
  FROM order_items i
  JOIN products p ON p.product_id = i.product_id
  LEFT JOIN category_translation t ON t.product_category_name = p.product_category_name
), main_pay AS (
  SELECT order_id, payment_type,
         ROW_NUMBER() OVER (PARTITION BY order_id ORDER BY payment_value DESC) AS rn
  FROM order_payments
)
SELECT o.order_id,
       date(o.order_purchase_timestamp) AS purchase_date,
       c.customer_state AS state_code,
       m.revenue, m.freight, m.items,
       mc.category,
       mp.payment_type,
       r.review_score,
       julianday(o.order_delivered_customer_date) - julianday(o.order_purchase_timestamp) AS days_to_deliver,
       julianday(o.order_delivered_customer_date) - julianday(o.order_estimated_delivery_date) AS days_vs_estimate
FROM orders o
JOIN customers c ON c.customer_id = o.customer_id
JOIN order_money m ON m.order_id = o.order_id
LEFT JOIN main_category mc ON mc.order_id = o.order_id AND mc.rn = 1
LEFT JOIN main_pay mp ON mp.order_id = o.order_id AND mp.rn = 1
LEFT JOIN latest_review r ON r.order_id = o.order_id AND r.rn = 1
WHERE o.order_status = 'delivered'
  AND o.order_delivered_customer_date IS NOT NULL
  AND o.order_purchase_timestamp >= '2017-01-01' AND o.order_purchase_timestamp < '2018-09-01'
"""


def main():
    con = sqlite3.connect(HERE / "olist.db")
    df = pd.read_sql_query(QUERY, con)
    con.close()

    df["state"] = df["state_code"].map(STATE_NAMES)
    df["is_late"] = (df["days_vs_estimate"] > 0).astype(int)
    df["days_to_deliver"] = df["days_to_deliver"].round(1)
    df["days_vs_estimate"] = df["days_vs_estimate"].round(1)
    df["delivery_timing"] = pd.cut(
        df["days_vs_estimate"],
        bins=[-1000, -7, 0, 3, 7, 1000],
        labels=["1) 7+ days early", "2) 0-7 days early", "3) 1-3 days late", "4) 4-7 days late", "5) 8+ days late"],
    ).astype(str)
    df = df[[
        "order_id", "purchase_date", "state", "state_code", "category", "payment_type",
        "items", "revenue", "freight", "review_score",
        "days_to_deliver", "days_vs_estimate", "delivery_timing", "is_late",
    ]]
    path = OUT / "olist_orders_for_tableau.csv"
    df.to_csv(path, index=False, encoding="utf-8-sig")  # BOM so accents (Ceará) open correctly
    print(f"{len(df):,} orders -> {path}")
    print("missing review_score:", int(df.review_score.isna().sum()), "| missing state:", int(df.state.isna().sum()),
          "| missing category:", int(df.category.isna().sum()), "| unknown category:", int((df.category == "unknown").sum()))
    print("totals: revenue %.0f | late %% %.1f | avg review %.2f" % (df.revenue.sum(), 100 * df.is_late.mean(), df.review_score.mean()))


if __name__ == "__main__":
    main()
