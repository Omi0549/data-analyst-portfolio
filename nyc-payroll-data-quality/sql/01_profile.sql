-- 01_profile.sql: profile the RAW data before touching it. Every number here feeds the findings in the README.

-- P1: Row counts per fiscal year and how many rows have an agency name (source completeness check).
SELECT fiscal_year,
       count(*)                                         AS rows,
       count(agency_name)                               AS rows_with_agency_name,
       round(100.0 * count(agency_name) / count(*), 1)  AS pct_with_agency_name
FROM raw_payroll
GROUP BY fiscal_year
ORDER BY fiscal_year;

-- P2: Completeness. Missing values per column across both years.
SELECT 'last_name' AS column_name, count(*) FILTER (WHERE last_name IS NULL) AS missing, count(*) AS total FROM raw_payroll
UNION ALL SELECT 'first_name', count(*) FILTER (WHERE first_name IS NULL), count(*) FROM raw_payroll
UNION ALL SELECT 'mid_init', count(*) FILTER (WHERE mid_init IS NULL), count(*) FROM raw_payroll
UNION ALL SELECT 'agency_start_date', count(*) FILTER (WHERE agency_start_date IS NULL), count(*) FROM raw_payroll
UNION ALL SELECT 'work_location_borough', count(*) FILTER (WHERE work_location_borough IS NULL), count(*) FROM raw_payroll
UNION ALL SELECT 'title_description', count(*) FILTER (WHERE title_description IS NULL), count(*) FROM raw_payroll
UNION ALL SELECT 'agency_name', count(*) FILTER (WHERE agency_name IS NULL), count(*) FROM raw_payroll
ORDER BY missing DESC;

-- P3: Consistency. Category columns and their distinct values (pay basis, leave status, borough).
SELECT 'pay_basis' AS field, pay_basis AS value, count(*) AS rows FROM raw_payroll GROUP BY pay_basis
UNION ALL SELECT 'leave_status', leave_status_as_of_june_30, count(*) FROM raw_payroll GROUP BY leave_status_as_of_june_30
UNION ALL SELECT 'borough', work_location_borough, count(*) FROM raw_payroll GROUP BY work_location_borough
ORDER BY field, rows DESC;

-- P4: Consistency. Job titles that differ only by capitalization or spacing (same title, several spellings).
SELECT upper(regexp_replace(trim(title_description), '\s+', ' ', 'g')) AS standardized_title,
       count(DISTINCT title_description)                               AS spellings,
       count(*)                                                        AS rows
FROM raw_payroll
GROUP BY 1
HAVING count(DISTINCT title_description) > 1
ORDER BY rows DESC
LIMIT 15;

-- P5: Uniqueness. Exact duplicate rows (every column identical) and the rows that exceed one copy.
SELECT count(*) AS duplicate_groups, sum(copies - 1) AS extra_rows
FROM (SELECT count(*) AS copies FROM stg_payroll GROUP BY row_hash HAVING count(*) > 1) d;

-- P6: Validity. Pay-rate ranges by pay basis show mislabeled and placeholder rates.
SELECT pay_basis_std,
       count(*)                                          AS rows,
       count(*) FILTER (WHERE dq_basis_mislabeled)       AS hourly_rate_looks_annual,
       count(*) FILTER (WHERE dq_placeholder_rate)       AS hourly_rate_2_or_less,
       count(*) FILTER (WHERE dq_daily_rate_low)         AS daily_rate_under_20,
       round(min(base_salary), 2)                        AS min_base,
       round(max(base_salary), 2)                        AS max_base
FROM stg_payroll
GROUP BY pay_basis_std
ORDER BY rows DESC;

-- P7: Validity. Negative or inconsistent hours and pay.
SELECT count(*) FILTER (WHERE dq_negative_hours)    AS negative_hours,
       count(*) FILTER (WHERE dq_negative_pay)      AS negative_regular_or_ot_pay,
       count(*) FILTER (WHERE dq_negative_other_pay) AS negative_other_pay,
       count(*) FILTER (WHERE dq_ot_inconsistent)   AS ot_hours_vs_pay_mismatch,
       count(*) FILTER (WHERE dq_hours_implausible) AS regular_hours_over_2500,
       count(*) FILTER (WHERE dq_invalid_start_date) AS invalid_start_date
FROM stg_payroll;

-- P8: Cross-year consistency. Same person, agency and title in both years but a different agency start date.
WITH a AS (
    SELECT payroll_number, last_name, first_name, mid_init, title_std, min(start_date_raw) AS start_date
    FROM stg_payroll WHERE fiscal_year = 2025 AND NOT dq_exact_duplicate GROUP BY 1, 2, 3, 4, 5
), b AS (
    SELECT payroll_number, last_name, first_name, mid_init, title_std, min(start_date_raw) AS start_date
    FROM stg_payroll WHERE fiscal_year = 2026 AND NOT dq_exact_duplicate GROUP BY 1, 2, 3, 4, 5
)
SELECT count(*)                                              AS people_in_both_years,
       count(*) FILTER (WHERE a.start_date <> b.start_date)  AS start_date_changed
FROM a JOIN b
  ON a.payroll_number = b.payroll_number
 AND a.last_name = b.last_name AND a.first_name = b.first_name
 AND a.mid_init IS NOT DISTINCT FROM b.mid_init     -- plain = would drop the 43% of people with no middle initial
 AND a.title_std IS NOT DISTINCT FROM b.title_std;
