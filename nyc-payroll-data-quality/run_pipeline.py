"""Run the whole data quality pipeline in one command: clean, validate, analyse, build the scorecard and charts.

Usage:  python run_pipeline.py            (re-run everything after raw_payroll is loaded)
        python run_pipeline.py --load     (also reload the raw CSVs first)
This is the recurring quality check described in docs/06_sop_quality_run.md. It stops on the first error.
"""
import os
import sys
import time

import build_scorecard
import load_raw
import make_charts
import run_sql
import stats_analysis

HERE = os.path.dirname(os.path.abspath(__file__))


def step(name, fn, *args):
    start = time.time()
    print(f"\n=== {name} ===")
    fn(*args)
    print(f"--- done in {time.time() - start:.0f}s")


if __name__ == "__main__":
    if "--load" in sys.argv:
        load_raw.ensure_database()
        step("Load raw CSVs", load_raw.load)
    for sql_file in ("02_clean.sql", "01_profile.sql", "03_validation.sql", "04_analysis.sql"):
        step(f"SQL {sql_file}", run_sql.main, os.path.join(HERE, "sql", sql_file))
    step("Statistical checks", stats_analysis.main)
    step("Excel scorecard", build_scorecard.main)
    step("Charts", make_charts.main)
    print("\nPipeline finished. Results are in outputs/")
