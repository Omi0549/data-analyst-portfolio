# Assumptions and Limitations

## Assumptions (each one changes the numbers if it is wrong)
1. **payroll_number identifies one agency.** Verified in the data: no payroll number has more than one agency name in FY2025. FY2026 agency names are rebuilt from this mapping, and all 158 FY2026 codes matched.
2. **260 workdays and 2,080 hours make a year.** Used to annualize daily and hourly rates. Real schedules vary (for example teachers, per-session work).
3. **Exact duplicates are errors.** Rows identical in all 17 columns are treated as accidental repeats. Only 18 rows were removed.
4. **Possible duplicates are not removed.** 320 rows share person, title and pay rate but differ in hours or pay. They could be real split appointments, so they are flagged for the data owner.
5. **Negative hours and pay are errors for pay totals.** They could be valid reversals, so the 5,199 curated rows with a critical problem (negative hours or pay, hours above 2,500, or a mislabeled pay basis) are quarantined from totals with `is_report_ready = FALSE`, not deleted.
6. **Negative "other pay" is kept.** 21,299 rows. It looks like normal adjustments and is only flagged.
7. **Thresholds are proposals.** The 2,500-hour limit, the $10,000 hourly-rate limit, the $2 placeholder limit and the $20 daily-rate floor are judgment calls, not rules from the publisher.

## Limitations
- **Employee identity is approximate.** The source has no employee ID, so people are matched on agency, name, middle initial and start date. Two people with identical values would merge, and a person who changes agency looks like a new person. Retention and employee counts are estimates.
- **Retention is "same agency".** It is not citywide retention. An employee who transferred agencies counts as not retained.
- **Two fiscal years only.** Trends and forecasting are not supported. Year-over-year changes can include retroactive pay and contract effects that this data cannot separate.
- **Salary comparisons are descriptive.** Borough differences mostly reflect which agencies and jobs sit there. Job title and union pay scale are not controlled for.
- **p-values are not informative at this size.** With about 329,000 salaried employees almost any difference is statistically significant, so effect sizes are reported.
- **The causes of defects are hypotheses.** Without access to the source systems, root causes in docs/05 are informed guesses to be confirmed.
- **Names are real public-record data.** They stay out of the repo and the curated table. The hashed employee_key pseudonymizes people and does not anonymize them.
