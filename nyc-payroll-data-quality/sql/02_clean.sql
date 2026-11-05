-- 02_clean.sql: raw_payroll (all text) -> dim_agency -> stg_payroll (typed + flagged) -> curated_payroll (privacy-safe, report-ready flag).
-- Principle: never silently delete or guess. Each defect gets a flag. Only exact duplicates are removed.
-- Every rule is documented in docs/02_data_dictionary.md and counted in sql/03_validation.sql.

-- Reference table: payroll_number -> agency_name. FY2026 rows have no agency name in the source, so this table rebuilds it.
DROP TABLE IF EXISTS dim_agency;
CREATE TABLE dim_agency AS
SELECT payroll_number::int AS payroll_number,
       min(upper(trim(agency_name))) AS agency_name
FROM raw_payroll
WHERE agency_name IS NOT NULL
GROUP BY payroll_number::int;
ALTER TABLE dim_agency ADD PRIMARY KEY (payroll_number);

DROP TABLE IF EXISTS stg_payroll;
CREATE TABLE stg_payroll AS
WITH typed AS (
    SELECT
        row_number() OVER (ORDER BY ctid)                                  AS raw_row_id,
        fiscal_year::int                                                   AS fiscal_year,
        make_date(fiscal_year::int, 6, 30)                                 AS fiscal_year_end,
        payroll_number::int                                                AS payroll_number,
        upper(regexp_replace(trim(last_name), '\s+', ' ', 'g'))            AS last_name,
        upper(regexp_replace(trim(first_name), '\s+', ' ', 'g'))           AS first_name,
        upper(trim(mid_init))                                              AS mid_init_raw,
        left(agency_start_date, 10)::date                                  AS start_date_raw,
        upper(trim(work_location_borough))                                 AS borough_raw,
        title_description                                                  AS title_raw,
        upper(regexp_replace(trim(title_description), '\s+', ' ', 'g'))    AS title_std,
        upper(trim(leave_status_as_of_june_30))                            AS leave_status,
        base_salary::numeric                                               AS base_salary,
        pay_basis                                                          AS pay_basis_raw,
        regular_hours::numeric                                             AS regular_hours,
        regular_gross_paid::numeric                                        AS regular_gross_paid,
        ot_hours::numeric                                                  AS ot_hours,
        total_ot_paid::numeric                                             AS total_ot_paid,
        total_other_pay::numeric                                           AS total_other_pay,
        -- hash of every source column: identical hashes are exact duplicate rows
        md5(concat_ws('|', fiscal_year, payroll_number, agency_name, last_name, first_name, mid_init,
            agency_start_date, work_location_borough, title_description, leave_status_as_of_june_30,
            base_salary, pay_basis, regular_hours, regular_gross_paid, ot_hours, total_ot_paid,
            total_other_pay))                                              AS row_hash
    FROM raw_payroll
), std AS (
    SELECT t.*,
        a.agency_name,
        -- start date: sentinel (9999-12-31), future and pre-1900 dates become NULL and are flagged
        CASE WHEN start_date_raw BETWEEN DATE '1900-01-01' AND fiscal_year_end THEN start_date_raw END AS start_date,
        CASE WHEN mid_init_raw ~ '^[A-Z]$' THEN mid_init_raw END           AS mid_init,
        CASE
            WHEN borough_raw IN ('MANHATTAN', 'BROOKLYN', 'QUEENS', 'BRONX') THEN borough_raw
            WHEN borough_raw = 'RICHMOND'                                    THEN 'STATEN ISLAND'
            WHEN borough_raw = 'OTHER'                                       THEN 'OTHER/UNSPECIFIED'
            WHEN borough_raw IS NULL OR borough_raw = ''                     THEN 'UNKNOWN'
            ELSE 'OUTSIDE NYC'
        END                                                                AS borough_std,
        CASE pay_basis_raw
            WHEN 'per Annum'       THEN 'ANNUAL'
            WHEN 'per Day'         THEN 'DAILY'
            WHEN 'per Hour'        THEN 'HOURLY'
            WHEN 'Prorated Annual' THEN 'PRORATED ANNUAL'
        END                                                                AS pay_basis_std,
        row_number() OVER (PARTITION BY row_hash ORDER BY raw_row_id)      AS dup_rank
    FROM typed t
    LEFT JOIN dim_agency a USING (payroll_number)
), flagged AS (
    SELECT s.*,
        -- DQ flags: TRUE means the rule failed
        (dup_rank > 1)                                                      AS dq_exact_duplicate,
        (last_name IS NULL OR first_name IS NULL)                           AS dq_missing_name,
        (title_raw IS NULL)                                                 AS dq_missing_title,
        (borough_std IN ('UNKNOWN', 'OTHER/UNSPECIFIED'))                   AS dq_borough_unspecified,
        (start_date IS NULL)                                                AS dq_invalid_start_date,
        (mid_init IS NULL AND mid_init_raw IS NOT NULL)                     AS dq_invalid_mid_init,
        (regular_hours < 0 OR ot_hours < 0)                                 AS dq_negative_hours,
        (regular_gross_paid < 0 OR total_ot_paid < 0)                       AS dq_negative_pay,
        (total_other_pay < 0)                                               AS dq_negative_other_pay,
        ((ot_hours = 0 AND total_ot_paid > 0) OR (ot_hours > 0 AND total_ot_paid = 0)) AS dq_ot_inconsistent,
        (regular_hours > 2500)                                              AS dq_hours_implausible,
        (pay_basis_std = 'HOURLY' AND base_salary > 10000)                  AS dq_basis_mislabeled,
        (pay_basis_std = 'HOURLY' AND base_salary <= 2)                     AS dq_placeholder_rate,
        (pay_basis_std = 'DAILY' AND base_salary < 20)                      AS dq_daily_rate_low,
        (agency_name IS NULL)                                               AS dq_agency_unmapped
    FROM std s
)
SELECT f.*,
    -- same appointment (person, title, pay rate) appearing more than once after exact duplicates are ignored
    (dup_rank = 1 AND sum((dup_rank = 1)::int) OVER (
        PARTITION BY fiscal_year, payroll_number, last_name, first_name, mid_init, start_date, title_std, base_salary, pay_basis_std
    ) > 1)                                                                  AS dq_possible_duplicate,
    -- annualized pay so hourly, daily and annual staff can be compared (assumes 260 workdays and 2,080 hours)
    CASE
        WHEN dq_basis_mislabeled OR dq_placeholder_rate OR dq_daily_rate_low THEN NULL
        WHEN pay_basis_std IN ('ANNUAL', 'PRORATED ANNUAL') THEN base_salary
        WHEN pay_basis_std = 'DAILY'  THEN base_salary * 260
        WHEN pay_basis_std = 'HOURLY' THEN base_salary * 2080
    END                                                                     AS annualized_base
FROM flagged f;

CREATE INDEX ON stg_payroll (fiscal_year);

-- Curated table: no names (privacy), exact duplicates removed, standardized values, and a report-ready flag.
-- employee_key is a one-way hash of name, agency and start date. It pseudonymizes people and is not true anonymization.
DROP TABLE IF EXISTS curated_payroll;
CREATE TABLE curated_payroll AS
SELECT
    md5(concat_ws('|', payroll_number, last_name, first_name, mid_init, start_date)) AS employee_key,
    fiscal_year,
    payroll_number,
    coalesce(agency_name, 'UNMAPPED AGENCY')                  AS agency_name,
    borough_std                                               AS work_borough,
    coalesce(title_std, 'UNKNOWN')                            AS title,
    leave_status,
    start_date,
    CASE WHEN start_date IS NOT NULL
         THEN round(((fiscal_year_end - start_date) / 365.25)::numeric, 1) END AS tenure_years,
    pay_basis_std                                             AS pay_basis,
    base_salary,
    annualized_base,
    regular_hours,
    ot_hours,
    regular_gross_paid,
    total_ot_paid,
    total_other_pay,
    regular_gross_paid + total_ot_paid + total_other_pay      AS gross_pay_total,
    dq_missing_name, dq_missing_title, dq_borough_unspecified, dq_invalid_start_date, dq_invalid_mid_init,
    dq_negative_hours, dq_negative_pay, dq_negative_other_pay, dq_ot_inconsistent, dq_hours_implausible,
    dq_basis_mislabeled, dq_placeholder_rate, dq_daily_rate_low, dq_agency_unmapped, dq_possible_duplicate,
    -- report-ready: passes every rule that would make pay totals unreliable
    NOT (dq_negative_hours OR dq_negative_pay OR dq_hours_implausible OR dq_basis_mislabeled) AS is_report_ready
FROM stg_payroll
WHERE NOT dq_exact_duplicate;

CREATE INDEX ON curated_payroll (fiscal_year, agency_name);
CREATE INDEX ON curated_payroll (employee_key);
ANALYZE stg_payroll;
ANALYZE curated_payroll;
