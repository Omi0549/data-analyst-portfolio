"""Load the Olist CSV files into a SQLite database (olist.db).

Run from the olist-sql-analysis folder:  python build_db.py
"""
import sqlite3
from pathlib import Path

import pandas as pd

HERE = Path(__file__).parent
DATA = HERE / "data"
DB = HERE / "olist.db"

# CSV file -> table name
TABLES = {
    "olist_customers_dataset.csv": "customers",
    "olist_geolocation_dataset.csv": "geolocation",
    "olist_orders_dataset.csv": "orders",
    "olist_order_items_dataset.csv": "order_items",
    "olist_order_payments_dataset.csv": "order_payments",
    "olist_order_reviews_dataset.csv": "order_reviews",
    "olist_products_dataset.csv": "products",
    "olist_sellers_dataset.csv": "sellers",
    "product_category_name_translation.csv": "category_translation",
}

# Timestamp columns are stored as ISO text so SQLite date functions work on them.
DATE_COLS = {
    "orders": [
        "order_purchase_timestamp",
        "order_approved_at",
        "order_delivered_carrier_date",
        "order_delivered_customer_date",
        "order_estimated_delivery_date",
    ],
    "order_items": ["shipping_limit_date"],
    "order_reviews": ["review_creation_date", "review_answer_timestamp"],
}


def main():
    if DB.exists():
        DB.unlink()
    con = sqlite3.connect(DB)
    for csv_name, table in TABLES.items():
        df = pd.read_csv(DATA / csv_name)
        for col in DATE_COLS.get(table, []):
            df[col] = pd.to_datetime(df[col]).dt.strftime("%Y-%m-%d %H:%M:%S")
        df.to_sql(table, con, index=False)
        print(f"{table:22s} {len(df):>9,d} rows")

    # Indexes on the join keys keep the multi-table queries fast.
    for stmt in [
        "CREATE INDEX idx_orders_id ON orders(order_id)",
        "CREATE INDEX idx_orders_cust ON orders(customer_id)",
        "CREATE INDEX idx_items_order ON order_items(order_id)",
        "CREATE INDEX idx_items_prod ON order_items(product_id)",
        "CREATE INDEX idx_items_seller ON order_items(seller_id)",
        "CREATE INDEX idx_pay_order ON order_payments(order_id)",
        "CREATE INDEX idx_rev_order ON order_reviews(order_id)",
        "CREATE INDEX idx_cust_id ON customers(customer_id)",
    ]:
        con.execute(stmt)
    con.commit()
    con.close()
    print("Built", DB)


if __name__ == "__main__":
    main()
