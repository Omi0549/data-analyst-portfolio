"""Load the raw NYC Citywide Payroll CSVs into PostgreSQL, unchanged, as text.

Raw layer rule: no type conversion and no cleaning here, so every defect in the source is preserved
and can be measured. Typing and cleaning happen later in sql/02_clean.sql.

Run from this folder:  python load_raw.py
Connection: database `nyc_payroll` on localhost. The password is read from pgpass.conf or PGPASSWORD,
never stored in code. Set NYC_PAYROLL_DSN to override the connection string.
"""
import csv
import glob
import os

import psycopg

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
ADMIN_DSN = os.environ.get("NYC_PAYROLL_ADMIN_DSN", "host=localhost dbname=postgres user=postgres")
DSN = os.environ.get("NYC_PAYROLL_DSN", "host=localhost dbname=nyc_payroll user=postgres")

COLUMNS = [
    "fiscal_year", "payroll_number", "agency_name", "last_name", "first_name", "mid_init",
    "agency_start_date", "work_location_borough", "title_description", "leave_status_as_of_june_30",
    "base_salary", "pay_basis", "regular_hours", "regular_gross_paid", "ot_hours",
    "total_ot_paid", "total_other_pay",
]


def ensure_database():
    with psycopg.connect(ADMIN_DSN, autocommit=True) as conn:
        exists = conn.execute("SELECT 1 FROM pg_database WHERE datname = 'nyc_payroll'").fetchone()
        if not exists:
            conn.execute("CREATE DATABASE nyc_payroll")


def load():
    with psycopg.connect(DSN, autocommit=True) as conn:
        cols = ",\n    ".join(f"{c} text" for c in COLUMNS)
        conn.execute("DROP TABLE IF EXISTS raw_payroll")
        conn.execute(f"CREATE TABLE raw_payroll (\n    {cols},\n    source_file text\n)")
        for path in sorted(glob.glob(os.path.join(DATA, "payroll_fy*.csv"))):
            name = os.path.basename(path)
            n = 0
            with open(path, newline="", encoding="utf-8") as f, \
                    conn.cursor() as cur, cur.copy("COPY raw_payroll FROM STDIN") as copy:
                reader = csv.DictReader(f)
                for row in reader:
                    # empty string in the CSV means the source value was blank: keep as NULL
                    copy.write_row([(row.get(c) or None) for c in COLUMNS] + [name])
                    n += 1
            print(f"{name}: {n:,} rows")
        conn.execute("ANALYZE raw_payroll")
        total = conn.execute("SELECT count(*) FROM raw_payroll").fetchone()[0]
        print(f"raw_payroll total: {total:,}")


if __name__ == "__main__":
    ensure_database()
    load()
