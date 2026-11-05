"""Run every statement in a .sql file against olist.db and print the results.

Usage:  python run_sql.py sql/00_data_checks.sql
Each result is also saved to outputs/<file name>_<n>.csv (n = statement number).
"""
import sqlite3
import sys
from pathlib import Path

import pandas as pd

HERE = Path(__file__).parent
pd.set_option("display.width", 200)
pd.set_option("display.max_columns", 30)
pd.set_option("display.max_rows", 60)


def main(sql_path):
    sql_file = Path(sql_path)
    text = sql_file.read_text(encoding="utf-8")
    con = sqlite3.connect(HERE / "olist.db")
    (HERE / "outputs").mkdir(exist_ok=True)
    statements = [s.strip() for s in text.split(";") if s.strip()]
    for n, stmt in enumerate(statements, 1):
        # Keep the comment lines so the output says what each query is for.
        comments = [l[2:].strip() for l in stmt.splitlines() if l.startswith("--")]
        title = next((c for c in comments if c.startswith("Q")), comments[0] if comments else "")
        df = pd.read_sql_query(stmt, con)
        print(f"\n[{n}] {title}\n{df.to_string(index=False)}")
        df.to_csv(HERE / "outputs" / f"{sql_file.stem}_{n}.csv", index=False)
    con.close()


if __name__ == "__main__":
    main(sys.argv[1])
