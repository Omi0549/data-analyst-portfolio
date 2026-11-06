"""Export small, aggregated star-schema CSVs from the curated payroll table for Power BI.

Why aggregated: the curated table has 1.1M rows. Power BI only needs counts and sums by agency,
borough, pay basis and fiscal year, so the CSVs stay tiny, contain no personal data, and are safe
to commit. Distinct employee counts are NOT additive across groups, so they are not exported here.

Run from this folder (needs the nyc_payroll database from run_pipeline.py):
    python export_for_powerbi.py
Password handling: same as ../load_raw.py (pgpass.conf or PGPASSWORD, never in a file).
"""
import os

import pandas as pd
import psycopg

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "data")
VALIDATION = os.path.join(HERE, "..", "outputs", "03_validation_1.csv")
RECON = os.path.join(HERE, "..", "outputs", "03_validation_2.csv")
CONN = os.environ.get("NYC_PAYROLL_DSN", "host=localhost dbname=nyc_payroll user=postgres")

# Row-level flag columns in curated_payroll, with a plain-English label for the report.
FLAGS = {
    "dq_missing_name": "Employee name missing",
    "dq_missing_title": "Job title missing",
    "dq_borough_unspecified": "Borough unknown or other",
    "dq_invalid_start_date": "Invalid start date",
    "dq_invalid_mid_init": "Invalid middle initial",
    "dq_negative_hours": "Negative hours",
    "dq_negative_pay": "Negative regular or overtime pay",
    "dq_negative_other_pay": "Negative other pay",
    "dq_ot_inconsistent": "Overtime hours and pay disagree",
    "dq_hours_implausible": "Regular hours above 2,500",
    "dq_basis_mislabeled": "Pay basis looks mislabeled",
    "dq_placeholder_rate": "Placeholder hourly rate",
    "dq_daily_rate_low": "Daily rate too low",
    "dq_agency_unmapped": "Agency code not mapped",
    "dq_possible_duplicate": "Possible duplicate",
}

FACT_SQL = f"""
SELECT fiscal_year, payroll_number, work_borough, pay_basis,
       COUNT(*)                                         AS records,
       COUNT(*) FILTER (WHERE is_report_ready)          AS report_ready_records,
       COUNT(*) FILTER (WHERE annualized_base IS NOT NULL) AS annualized_records,
       COALESCE(SUM(annualized_base), 0)                AS annualized_base_sum,
       COALESCE(SUM(gross_pay_total)  FILTER (WHERE is_report_ready), 0) AS gross_pay,
       COALESCE(SUM(total_ot_paid)    FILTER (WHERE is_report_ready), 0) AS overtime_pay,
       COALESCE(SUM(regular_gross_paid) FILTER (WHERE is_report_ready), 0) AS regular_pay,
       COALESCE(SUM(ot_hours)         FILTER (WHERE is_report_ready), 0) AS overtime_hours,
       COUNT(*) FILTER (WHERE {' OR '.join(FLAGS)})     AS records_with_warning
FROM curated_payroll
GROUP BY fiscal_year, payroll_number, work_borough, pay_basis
ORDER BY 1, 2, 3, 4
"""

FLAG_SQL = "SELECT fiscal_year, payroll_number, " + ", ".join(
    f"COUNT(*) FILTER (WHERE {c}) AS {c}" for c in FLAGS
) + " FROM curated_payroll GROUP BY 1, 2 ORDER BY 1, 2"

AGENCY_SQL = "SELECT payroll_number, MAX(agency_name) AS agency_name FROM curated_payroll GROUP BY 1 ORDER BY 1"


def main():
    os.makedirs(OUT, exist_ok=True)
    with psycopg.connect(CONN) as conn:
        cur = conn.execute(FACT_SQL)
        fact = pd.DataFrame(cur.fetchall(), columns=[d.name for d in cur.description])
        flags = pd.DataFrame(conn.execute(FLAG_SQL).fetchall(), columns=["fiscal_year", "payroll_number", *FLAGS])
        agency = pd.DataFrame(conn.execute(AGENCY_SQL).fetchall(), columns=["payroll_number", "agency_name"])

    # Long format: one row per year, agency and issue. Easier to slice in Power BI than 15 columns.
    long = flags.melt(id_vars=["fiscal_year", "payroll_number"], var_name="issue_code", value_name="records_flagged")
    long = long[long["records_flagged"] > 0]

    dim_issue = pd.DataFrame({"issue_code": list(FLAGS), "issue_name": list(FLAGS.values())})
    dim_borough = pd.DataFrame({"work_borough": sorted(fact["work_borough"].dropna().unique())})
    dim_basis = pd.DataFrame({"pay_basis": sorted(fact["pay_basis"].dropna().unique())})
    dim_year = pd.DataFrame({"fiscal_year": sorted(fact["fiscal_year"].unique())})
    dim_year["fiscal_year_label"] = "FY" + dim_year["fiscal_year"].astype(str)
    dim_year["period_start"] = pd.to_datetime((dim_year["fiscal_year"] - 1).astype(str) + "-07-01").dt.date
    dim_year["period_end"] = pd.to_datetime(dim_year["fiscal_year"].astype(str) + "-06-30").dt.date

    rules = pd.read_csv(VALIDATION)
    recon = pd.read_csv(RECON)

    files = {
        "fact_payroll.csv": fact, "fact_issue_by_agency.csv": long,
        "dim_agency.csv": agency, "dim_borough.csv": dim_borough, "dim_pay_basis.csv": dim_basis,
        "dim_year.csv": dim_year, "dim_issue.csv": dim_issue,
        "dq_rules.csv": rules, "dq_reconciliation.csv": recon,
    }
    for name, df in files.items():
        df.to_csv(os.path.join(OUT, name), index=False)
        print(f"{name:28s} {len(df):>7,} rows")

    # Control totals to check the Power BI report against (see POWERBI_GUIDE.md)
    print("\nControl totals (report-ready rows):")
    print(fact.groupby("fiscal_year")[["records", "report_ready_records", "gross_pay", "overtime_pay"]].sum())


if __name__ == "__main__":
    main()
