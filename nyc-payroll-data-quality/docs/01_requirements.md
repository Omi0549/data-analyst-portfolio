# Business Requirements

**Status:** simulated for this portfolio case study. No real stakeholder interviews took place. The stakeholders, requests and thresholds below were written by the author to practise turning business needs into testable requirements. A real engagement would confirm each one with the people named.

## Context
The City publishes employee-level payroll data every fiscal year (July 1 to June 30). Imagine a team that wants to use two years of it (FY2025 and FY2026, 1.11 million rows) to track workforce cost and overtime, and needs to trust the numbers first.

## Stakeholders and what they asked for (simulated)

| Stakeholder | Pain point | Ask |
|---|---|---|
| Workforce analytics lead | "Headcount and pay totals change depending on who runs the report." | One agreed, repeatable set of cleaning rules |
| Budget / finance analyst | "I need pay comparable across hourly, daily and salaried staff." | Annualized pay on a common basis |
| Data engineering lead | "Tell us exactly which source fields are broken so we can fix them upstream." | A ranked list of defects with counts and examples |
| Privacy and compliance officer | "Analysts should not carry employee names around." | Curated data without names |

## Requirements and acceptance criteria

| ID | Requirement | Acceptance criterion (testable) | Checked by |
|---|---|---|---|
| REQ-01 | Each appointment appears once per fiscal year | Exact duplicate rows = 0 in curated data. Possible duplicates at or below 0.1% and listed for review | R01, R02 |
| REQ-02 | Key descriptive fields are complete | Agency name present on 100% of rows. Name, title and start date each missing in at most 0.1%. Borough unknown at most 1% | R03 to R06 |
| REQ-03 | Values are valid | No negative hours or regular/overtime pay in report-ready rows. Start date not in the future or a placeholder. Regular hours at most 2,500 | R07 to R10 |
| REQ-04 | Values are consistent | Titles and boroughs use one standard spelling. Overtime hours and overtime pay agree in at least 99.9% of rows. Pay basis matches the size of the rate | R11 to R14 |
| REQ-05 | Pay is comparable | Annualized base pay available for at least 95% of rows | R15 |
| REQ-06 | Numbers reconcile | Row counts and total pay tie out between raw and curated data for each year. Cross-year conflicts are reported | V2, V3, P8 |
| REQ-07 | Privacy | Curated table has no name columns. The repo contains no raw files | V4 |

Thresholds are proposed targets. They are judgment calls to agree with the data owner.

## Open questions I would ask stakeholders
1. Are negative pay and hours reversals of earlier payments (valid adjustments) or entry errors?
2. Why does the FY2026 extract have no agency name? Is that a publishing change or a defect?
3. Should the very low "per Hour" rates (for example $1.00 for poll workers) be read as a flat stipend rather than an hourly wage?
4. Is a person with two rows for the same title and pay rate a real second appointment or a duplicate?
5. Which agency start date is authoritative when it differs between years?
6. What reporting cadence (monthly, per fiscal year) and who owns fixes at each agency?
