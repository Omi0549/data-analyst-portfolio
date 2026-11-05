-- 03_validation.sql: check the cleaned data against the written requirements (docs/01_requirements.md).
-- Each rule returns failed rows, total rows, failure %, the agreed threshold, and PASS/FAIL.
-- RAW = stg_payroll (before cleaning). CURATED = curated_payroll (after cleaning, report-ready rows only).
-- Thresholds are proposed targets for this case study. A real team would agree them with the data owner.

-- V1: Rule results before cleaning (RAW) and after cleaning (CURATED).
WITH raw_rules AS (
    SELECT 'R01' AS rule_id, 'REQ-01' AS req_id, 'Exact duplicate rows' AS rule, count(*) FILTER (WHERE dq_exact_duplicate) AS failed, count(*) AS total, 0.0 AS threshold_pct FROM stg_payroll
    UNION ALL SELECT 'R02', 'REQ-01', 'Same appointment and pay rate recorded twice (possible duplicate)', count(*) FILTER (WHERE dq_possible_duplicate), count(*), 0.1 FROM stg_payroll
    UNION ALL SELECT 'R03', 'REQ-02', 'Agency name missing (FY2026 source gap)', count(*) FILTER (WHERE agency_name IS NULL), count(*), 0.0 FROM raw_payroll
    UNION ALL SELECT 'R04', 'REQ-02', 'First or last name missing', count(*) FILTER (WHERE dq_missing_name), count(*), 0.1 FROM stg_payroll
    UNION ALL SELECT 'R05', 'REQ-02', 'Job title missing', count(*) FILTER (WHERE dq_missing_title), count(*), 0.1 FROM stg_payroll
    UNION ALL SELECT 'R06', 'REQ-02', 'Work borough unknown or OTHER', count(*) FILTER (WHERE dq_borough_unspecified), count(*), 1.0 FROM stg_payroll
    UNION ALL SELECT 'R07', 'REQ-03', 'Agency start date invalid (9999 sentinel, future or missing)', count(*) FILTER (WHERE dq_invalid_start_date), count(*), 0.1 FROM stg_payroll
    UNION ALL SELECT 'R08', 'REQ-03', 'Negative regular or overtime hours', count(*) FILTER (WHERE dq_negative_hours), count(*), 0.0 FROM stg_payroll
    UNION ALL SELECT 'R09', 'REQ-03', 'Negative regular or overtime pay', count(*) FILTER (WHERE dq_negative_pay), count(*), 0.0 FROM stg_payroll
    UNION ALL SELECT 'R10', 'REQ-03', 'Regular hours above 2,500', count(*) FILTER (WHERE dq_hours_implausible), count(*), 0.0 FROM stg_payroll
    UNION ALL SELECT 'R11', 'REQ-04', 'Overtime hours and overtime pay disagree (one is zero)', count(*) FILTER (WHERE dq_ot_inconsistent), count(*), 0.1 FROM stg_payroll
    UNION ALL SELECT 'R12', 'REQ-04', 'Job title spelled differently from its standard form', count(*) FILTER (WHERE title_raw IS NOT NULL AND title_raw <> title_std), count(*), 0.0 FROM stg_payroll
    UNION ALL SELECT 'R13', 'REQ-04', 'Borough uses a non-standard name (RICHMOND)', count(*) FILTER (WHERE borough_raw = 'RICHMOND'), count(*), 0.0 FROM stg_payroll
    UNION ALL SELECT 'R14', 'REQ-04', 'Hourly pay basis with an annual-sized rate (over $10,000)', count(*) FILTER (WHERE dq_basis_mislabeled), count(*), 0.0 FROM stg_payroll
    UNION ALL SELECT 'R15', 'REQ-05', 'Pay cannot be annualized (placeholder, mislabeled or low rate)', count(*) FILTER (WHERE annualized_base IS NULL), count(*), 5.0 FROM stg_payroll
), cur_rules AS (
    SELECT 'R01' AS rule_id, count(*) FILTER (WHERE false) AS failed, count(*) AS total FROM curated_payroll
    UNION ALL SELECT 'R02', count(*) FILTER (WHERE dq_possible_duplicate), count(*) FROM curated_payroll
    UNION ALL SELECT 'R03', count(*) FILTER (WHERE agency_name = 'UNMAPPED AGENCY'), count(*) FROM curated_payroll
    UNION ALL SELECT 'R04', count(*) FILTER (WHERE dq_missing_name), count(*) FROM curated_payroll
    UNION ALL SELECT 'R05', count(*) FILTER (WHERE dq_missing_title), count(*) FROM curated_payroll
    UNION ALL SELECT 'R06', count(*) FILTER (WHERE dq_borough_unspecified), count(*) FROM curated_payroll
    UNION ALL SELECT 'R07', count(*) FILTER (WHERE dq_invalid_start_date), count(*) FROM curated_payroll
    UNION ALL SELECT 'R08', count(*) FILTER (WHERE dq_negative_hours), count(*) FROM curated_payroll WHERE is_report_ready
    UNION ALL SELECT 'R09', count(*) FILTER (WHERE dq_negative_pay), count(*) FROM curated_payroll WHERE is_report_ready
    UNION ALL SELECT 'R10', count(*) FILTER (WHERE dq_hours_implausible), count(*) FROM curated_payroll WHERE is_report_ready
    UNION ALL SELECT 'R11', count(*) FILTER (WHERE dq_ot_inconsistent), count(*) FROM curated_payroll
    UNION ALL SELECT 'R12', count(*) FILTER (WHERE title <> upper(regexp_replace(trim(title), '\s+', ' ', 'g'))), count(*) FROM curated_payroll
    UNION ALL SELECT 'R13', count(*) FILTER (WHERE work_borough = 'RICHMOND'), count(*) FROM curated_payroll
    UNION ALL SELECT 'R14', count(*) FILTER (WHERE dq_basis_mislabeled), count(*) FROM curated_payroll WHERE is_report_ready
    UNION ALL SELECT 'R15', count(*) FILTER (WHERE annualized_base IS NULL), count(*) FROM curated_payroll
)
SELECT r.rule_id, r.req_id, r.rule,
       r.failed                                           AS raw_failed,
       r.total                                            AS raw_total,
       round(100.0 * r.failed / r.total, 3)               AS raw_fail_pct,
       c.failed                                           AS curated_failed,
       c.total                                            AS curated_total,
       round(100.0 * c.failed / c.total, 3)               AS curated_fail_pct,
       r.threshold_pct,
       CASE WHEN 100.0 * c.failed / c.total <= r.threshold_pct THEN 'PASS' ELSE 'FAIL' END AS curated_status
FROM raw_rules r
JOIN cur_rules c USING (rule_id)
ORDER BY r.rule_id;

-- V2: Reconciliation (REQ-06). Row counts must tie out: raw rows minus removed duplicates equals curated rows, per year.
SELECT r.fiscal_year,
       r.raw_rows,
       s.exact_duplicates_removed,
       c.curated_rows,
       r.raw_rows - s.exact_duplicates_removed = c.curated_rows AS rows_reconcile
FROM (SELECT fiscal_year::int AS fiscal_year, count(*) AS raw_rows FROM raw_payroll GROUP BY 1) r
JOIN (SELECT fiscal_year, count(*) FILTER (WHERE dq_exact_duplicate) AS exact_duplicates_removed FROM stg_payroll GROUP BY 1) s USING (fiscal_year)
JOIN (SELECT fiscal_year, count(*) AS curated_rows FROM curated_payroll GROUP BY 1) c USING (fiscal_year)
ORDER BY r.fiscal_year;

-- V3: Reconciliation (REQ-06). Total pay must tie out between raw and curated (to the cent) after removing duplicates.
SELECT (SELECT round(sum(regular_gross_paid + total_ot_paid + total_other_pay), 2) FROM stg_payroll WHERE NOT dq_exact_duplicate) AS staging_total_pay,
       (SELECT round(sum(gross_pay_total), 2) FROM curated_payroll) AS curated_total_pay,
       (SELECT round(sum(regular_gross_paid + total_ot_paid + total_other_pay), 2) FROM stg_payroll WHERE NOT dq_exact_duplicate)
       = (SELECT round(sum(gross_pay_total), 2) FROM curated_payroll) AS totals_reconcile;

-- V4: Privacy (REQ-07). The curated table must not contain any name column. Expect zero rows.
SELECT column_name
FROM information_schema.columns
WHERE table_name = 'curated_payroll' AND column_name IN ('last_name', 'first_name', 'mid_init');

-- V5: Agency back-fill (REQ-02). Every FY2026 payroll number must map to an agency known from FY2025.
SELECT count(*) AS fy2026_rows,
       count(*) FILTER (WHERE agency_name = 'UNMAPPED AGENCY') AS unmapped_rows,
       count(DISTINCT payroll_number) AS agency_codes,
       count(DISTINCT payroll_number) FILTER (WHERE agency_name = 'UNMAPPED AGENCY') AS unmapped_codes
FROM curated_payroll
WHERE fiscal_year = 2026;
