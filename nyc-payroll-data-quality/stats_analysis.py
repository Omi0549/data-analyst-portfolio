"""Statistical checks on the curated payroll data (FY2026, salaried employees with a usable pay rate).

Questions: (1) Does pay rise with tenure? (2) Do median salaries differ between Manhattan and Brooklyn?
Run from this folder:  python stats_analysis.py     Output is also saved to outputs/stats_output.txt
Connection: see load_raw.py (password from pgpass.conf or PGPASSWORD).
"""
import io
import os
from contextlib import redirect_stdout

import numpy as np
import pandas as pd
import psycopg
import statsmodels.formula.api as smf
from scipy import stats

HERE = os.path.dirname(os.path.abspath(__file__))
DSN = os.environ.get("NYC_PAYROLL_DSN", "host=localhost dbname=nyc_payroll user=postgres")

QUERY = """
SELECT employee_key, work_borough, tenure_years, annualized_base
FROM curated_payroll
WHERE is_report_ready AND fiscal_year = 2026 AND pay_basis = 'ANNUAL'
  AND annualized_base IS NOT NULL AND annualized_base >= 10000 AND tenure_years IS NOT NULL
  AND work_borough IN ('MANHATTAN', 'BROOKLYN', 'QUEENS', 'BRONX', 'STATEN ISLAND')
"""


def analyse():
    with psycopg.connect(DSN) as conn:
        df = pd.read_sql(QUERY, conn)
    df["annualized_base"] = df["annualized_base"].astype(float)
    df["tenure_years"] = df["tenure_years"].astype(float)
    print(f"Rows analysed: {len(df):,} salaried employees, FY2026")

    # 1. Rank correlation: robust to the skewed pay distribution
    rho, p = stats.spearmanr(df["tenure_years"], df["annualized_base"])
    print(f"\n1) Spearman correlation, tenure vs annual base pay: rho = {rho:.3f} (p = {p:.2g})")

    # 2. Regression: log pay on tenure and borough (Bronx as reference)
    df["log_pay"] = np.log(df["annualized_base"])
    model = smf.ols("log_pay ~ tenure_years + C(work_borough, Treatment('BRONX'))", data=df).fit(cov_type="HC3")
    print("\n2) OLS on log(annual base pay), robust standard errors")
    print(model.summary().tables[1])
    print(f"R-squared: {model.rsquared:.3f}. Each extra year of tenure is associated with "
          f"{100 * (np.exp(model.params['tenure_years']) - 1):.2f}% higher base pay.")

    # 3. Manhattan vs Brooklyn: Mann-Whitney U with an effect size (p-values are tiny at this sample size)
    man = df.loc[df["work_borough"] == "MANHATTAN", "annualized_base"]
    bk = df.loc[df["work_borough"] == "BROOKLYN", "annualized_base"]
    u, p_u = stats.mannwhitneyu(man, bk, alternative="two-sided")
    rank_biserial = 2 * u / (len(man) * len(bk)) - 1
    print(f"\n3) Mann-Whitney U, Manhattan vs Brooklyn: p = {p_u:.2g}, rank-biserial effect size = {rank_biserial:.3f}")
    print(f"   Medians: Manhattan ${man.median():,.0f}, Brooklyn ${bk.median():,.0f}")
    print("\nCaveat: this is descriptive. Job title, agency and union scale are not controlled for, so borough "
          "differences mostly reflect which agencies and jobs are located there.")


def main():
    buf = io.StringIO()
    with redirect_stdout(buf):
        analyse()
    text = buf.getvalue()
    print(text)
    os.makedirs(os.path.join(HERE, "outputs"), exist_ok=True)
    with open(os.path.join(HERE, "outputs", "stats_output.txt"), "w", encoding="utf-8") as f:
        f.write(text)


if __name__ == "__main__":
    main()
