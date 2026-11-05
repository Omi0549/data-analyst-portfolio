-- 04_analysis.sql: business analysis on report-ready curated rows (is_report_ready = TRUE). Shows what the cleaned data can answer.

-- A1: City payroll by fiscal year: pay records, distinct employees, gross pay and overtime share.
SELECT fiscal_year,
       count(*)                                               AS pay_records,
       count(DISTINCT employee_key)                           AS employees,
       round(sum(gross_pay_total) / 1e9, 2)                   AS gross_pay_billion_usd,
       round(100 * sum(total_ot_paid) / sum(gross_pay_total), 2) AS overtime_pct_of_gross
FROM curated_payroll
WHERE is_report_ready
GROUP BY fiscal_year
ORDER BY fiscal_year;

-- A2: Top 10 agencies by FY2026 gross pay with change versus FY2025.
WITH agency_year AS (
    SELECT agency_name, fiscal_year, sum(gross_pay_total) AS pay
    FROM curated_payroll
    WHERE is_report_ready
    GROUP BY agency_name, fiscal_year
), pivoted AS (
    SELECT agency_name,
           max(pay) FILTER (WHERE fiscal_year = 2025) AS pay_fy2025,
           max(pay) FILTER (WHERE fiscal_year = 2026) AS pay_fy2026
    FROM agency_year
    GROUP BY agency_name
)
SELECT rank() OVER (ORDER BY pay_fy2026 DESC)                        AS rnk,
       agency_name,
       round(pay_fy2025 / 1e6, 1)                                    AS fy2025_million,
       round(pay_fy2026 / 1e6, 1)                                    AS fy2026_million,
       round(100 * (pay_fy2026 - pay_fy2025) / pay_fy2025, 1)        AS pct_change
FROM pivoted
WHERE pay_fy2025 IS NOT NULL AND pay_fy2026 IS NOT NULL
ORDER BY pay_fy2026 DESC
LIMIT 10;

-- A3: Overtime concentration in FY2026: what share of all overtime pay goes to the top 5% of overtime earners (NTILE window).
WITH emp_ot AS (
    SELECT employee_key, sum(total_ot_paid) AS ot_paid
    FROM curated_payroll
    WHERE is_report_ready AND fiscal_year = 2026
    GROUP BY employee_key
), bucketed AS (
    SELECT ot_paid, ntile(20) OVER (ORDER BY ot_paid DESC) AS twentieth
    FROM emp_ot
    WHERE ot_paid > 0
)
SELECT count(*)                                                       AS employees_with_overtime,
       round(sum(ot_paid) / 1e6, 1)                                   AS total_overtime_million,
       round(100 * sum(ot_paid) FILTER (WHERE twentieth = 1) / sum(ot_paid), 1) AS pct_of_ot_to_top_5pct
FROM bucketed;

-- A4: Same-agency retention proxy: ACTIVE FY2025 employees who appear again in FY2026, lowest 10 among agencies with 2,000+ employees.
WITH y25 AS (
    SELECT DISTINCT employee_key, agency_name
    FROM curated_payroll
    WHERE fiscal_year = 2025 AND leave_status = 'ACTIVE' AND is_report_ready
), y26 AS (
    SELECT DISTINCT employee_key FROM curated_payroll WHERE fiscal_year = 2026
)
SELECT y25.agency_name,
       count(*)                                                 AS active_fy2025,
       count(y26.employee_key)                                  AS present_fy2026,
       round(100.0 * count(y26.employee_key) / count(*), 1)     AS pct_retained
FROM y25
LEFT JOIN y26 USING (employee_key)
GROUP BY y25.agency_name
HAVING count(*) >= 2000
ORDER BY pct_retained ASC
LIMIT 10;

-- A5: Median annualized base pay by work borough, FY2026, salaried (ANNUAL) employees with a usable pay rate.
SELECT work_borough,
       count(*)                                                                    AS employees,
       round(percentile_cont(0.5) WITHIN GROUP (ORDER BY annualized_base)::numeric) AS median_annual_base
FROM curated_payroll
WHERE is_report_ready AND fiscal_year = 2026 AND pay_basis = 'ANNUAL' AND annualized_base IS NOT NULL
  AND work_borough IN ('MANHATTAN', 'BROOKLYN', 'QUEENS', 'BRONX', 'STATEN ISLAND')
GROUP BY work_borough
ORDER BY median_annual_base DESC;

-- A6: Data quality by agency, FY2026: which agencies have the most records needing attention (for source-system fixes).
SELECT agency_name,
       count(*)                                                                  AS records,
       count(*) FILTER (WHERE dq_missing_name OR dq_missing_title OR dq_borough_unspecified
                           OR dq_invalid_start_date OR dq_ot_inconsistent OR dq_negative_other_pay
                           OR dq_possible_duplicate)                             AS records_with_warning,
       count(*) FILTER (WHERE NOT is_report_ready)                               AS records_quarantined,
       round(100.0 * count(*) FILTER (WHERE dq_missing_name OR dq_missing_title OR dq_borough_unspecified
                           OR dq_invalid_start_date OR dq_ot_inconsistent OR dq_negative_other_pay
                           OR dq_possible_duplicate) / count(*), 1)              AS pct_with_warning
FROM curated_payroll
WHERE fiscal_year = 2026
GROUP BY agency_name
HAVING count(*) >= 1000
ORDER BY pct_with_warning DESC
LIMIT 10;
