# Standard Operating Procedure: Recurring Data Quality Run

**Purpose:** repeat the same checks every time new payroll data arrives, so results are comparable over time.
**When:** after each new fiscal-year file is published, or monthly during a review.
**Who:** the data analyst on the team.

## Steps
1. **Get the data.** Download the new fiscal-year CSV from the NYC Open Data API into `data/` and name it `payroll_fy<year>.csv`. Never edit the file by hand.
2. **Check access.** The PostgreSQL password comes from `pgpass.conf` or `PGPASSWORD`. Never put it in a file in the repo.
3. **Run the pipeline:** `python run_pipeline.py --load` (add `--load` only when raw files changed). It reloads, cleans, validates, analyses and rebuilds the scorecard and charts. It stops on the first error.
4. **Read the scorecard** (`outputs/dq_scorecard.xlsx`):
   - Summary sheet: pass rate and rows kept.
   - Rule Scorecard: any FAIL needs an owner and a follow-up.
   - Reconciliation: every year must show YES.
5. **Compare with the last run.** If a rule's failure count jumps, check for a schema change first (a missing column or a new category).
6. **Escalate.** Send failing rules to the data owner with counts and the example query from `sql/03_validation.sql`.
7. **Record.** Save the scorecard with the date, and note any change to rules, thresholds or assumptions in the docs.

## Stop conditions (do not publish results)
- Row counts do not reconcile.
- Total pay differs between raw and curated data.
- The curated table contains a name column.
- A required column is empty (as happened with agency name in FY2026).

## Data handling
- Raw files contain employee names. Keep them out of the repo, email and shared folders.
- Share only the curated outputs and aggregated results.
