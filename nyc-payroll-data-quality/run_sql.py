"""Run a .sql file against the nyc_payroll database and save every SELECT result as a CSV.

Usage:  python run_sql.py sql\\01_profile.sql
Results go to outputs\\<file>_<n>.csv and are also printed. Password handling: see load_raw.py.
"""
import csv
import os
import re
import sys

import psycopg

HERE = os.path.dirname(os.path.abspath(__file__))
CONN = os.environ.get("NYC_PAYROLL_DSN", "host=localhost dbname=nyc_payroll user=postgres")


def split_statements(sql):
    """Strip -- comments first (they may contain semicolons), then split on ;"""
    no_comments = "\n".join(re.sub(r"--.*$", "", line) for line in sql.splitlines())
    return [s.strip() for s in no_comments.split(";") if s.strip()]


def main(path):
    stem = os.path.splitext(os.path.basename(path))[0]
    out_dir = os.path.join(HERE, "outputs")
    os.makedirs(out_dir, exist_ok=True)
    with open(path, encoding="utf-8") as f:
        statements = split_statements(f.read())
    with psycopg.connect(CONN, autocommit=True) as conn:
        for i, stmt in enumerate(statements, start=1):
            cur = conn.execute(stmt)
            if cur.description is None:      # DDL such as CREATE VIEW
                print(f"[{i}] ok")
                continue
            cols = [d.name for d in cur.description]
            rows = cur.fetchall()
            out = os.path.join(out_dir, f"{stem}_{i}.csv")
            with open(out, "w", newline="", encoding="utf-8") as f:
                w = csv.writer(f)
                w.writerow(cols)
                w.writerows(rows)
            print(f"[{i}] {len(rows)} rows -> {os.path.relpath(out, HERE)}")
            print("   ", cols)
            for r in rows[:12]:
                print("   ", r)


if __name__ == "__main__":
    main(sys.argv[1])
