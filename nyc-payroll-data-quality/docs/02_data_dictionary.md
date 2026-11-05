# Data Dictionary

Source: NYC Open Data, "Citywide Payroll Data (Fiscal Year)", published by the NYC Office of Payroll Administration. Field descriptions below are the author's, based on the observed values. Check the publisher's own dictionary for official definitions.

Sensitivity levels: **Personal** (identifies a person), **Internal** (pay and employment details), **Public reference** (codes and labels).

## Source fields (raw_payroll, all stored as text)

| Field | Type after cleaning | Description | Example | Sensitivity | Known issues and rule |
|---|---|---|---|---|---|
| fiscal_year | integer | NYC fiscal year, July 1 to June 30. FY2026 ends 2026-06-30 | 2026 | Public reference | None found |
| payroll_number | integer | Agency code. One code maps to one agency name | 67 | Public reference | None found. Used to rebuild missing agency names |
| agency_name | text | Agency name. **Missing in all FY2026 rows** | ADMIN FOR CHILDREN'S SVCS | Public reference | R03: back-filled from payroll_number |
| last_name, first_name | text | Employee name | (not shown) | **Personal** | R04: 756 rows missing. Dropped from curated data |
| mid_init | char | Middle initial. Missing for 43% of rows | S | **Personal** | Non-letters (for example "-", "0", "(") set to NULL, 87 rows |
| agency_start_date | date | Date the employee started at the agency | 2013-02-04 | Internal | R07: 40 rows invalid (9999-12-31 placeholder or after fiscal year end), set to NULL |
| work_location_borough | text | Borough or county of the work location | MANHATTAN | Public reference | R13: RICHMOND renamed STATEN ISLAND. R06: 5,881 unknown or OTHER |
| title_description | text | Civil service job title | PROGRAM EVALUATOR | Public reference | R12: 10,898 rows differ only by capitalization. R05: 96 missing |
| leave_status_as_of_june_30 | text | ACTIVE, CEASED, ON LEAVE, SEASONAL, ON SEPARATION LEAVE | ACTIVE | Internal | None found |
| base_salary | numeric | Pay rate. **Unit depends on pay_basis** (year, day or hour) | 95897.00 | Internal | R14, R15: unit mismatches and placeholders |
| pay_basis | text | per Annum, per Day, per Hour, Prorated Annual | per Annum | Public reference | Standardized to ANNUAL, DAILY, HOURLY, PRORATED ANNUAL |
| regular_hours | numeric | Regular hours paid in the fiscal year | 1820 | Internal | R08: negative in some rows. R10: above 2,500 |
| regular_gross_paid | numeric | Regular gross pay for the year, USD | 89097.13 | Internal | R09: negative in some rows |
| ot_hours | numeric | Overtime hours | 73 | Internal | R08, R11 |
| total_ot_paid | numeric | Overtime pay, USD | 4291.75 | Internal | R09, R11 |
| total_other_pay | numeric | Other pay such as differentials and adjustments, USD | 699.41 | Internal | Negative in 21,299 rows. Treated as possible valid adjustments, flagged only |

## Fields created by the pipeline (curated_payroll)

| Field | Description | How it is calculated |
|---|---|---|
| employee_key | Pseudonymous person key | MD5 of agency code, last name, first name, middle initial and start date. Pseudonymization, not anonymization |
| work_borough | Standard borough | Mapping above. Counties outside the city become OUTSIDE NYC |
| title | Standard title | Upper case, extra spaces removed, NULL becomes UNKNOWN |
| tenure_years | Years of service at fiscal year end | (June 30 of the fiscal year minus start date) / 365.25. NULL if start date invalid |
| annualized_base | Base pay as a yearly amount | ANNUAL and PRORATED use base_salary. DAILY x 260. HOURLY x 2,080. NULL if flagged R14, R15 or low daily rate |
| gross_pay_total | Total pay | regular_gross_paid + total_ot_paid + total_other_pay |
| dq_* flags | One TRUE/FALSE column per rule | See sql/02_clean.sql |
| is_report_ready | Safe for pay totals | FALSE if negative hours, negative regular or overtime pay, hours above 2,500, or mislabeled pay basis |

## Metric definitions

| Metric | Definition |
|---|---|
| Failure % | Rows failing a rule divided by rows checked, times 100 |
| Pass rate | Rules whose curated failure % is at or below the threshold, divided by rules checked |
| Overtime share | Sum of total_ot_paid divided by sum of gross_pay_total, report-ready rows |
| Employees | Distinct employee_key values (an approximation, see limitations) |
| Same-agency retention | Share of ACTIVE FY2025 employees whose employee_key appears again in FY2026 |
