# Process Improvement Recommendations

The causes below are **hypotheses** based on the patterns in the data. Confirm each with the data owner before acting.

| # | Recurring issue (evidence) | Likely cause (hypothesis) | Recommended control | Prevents |
|---|---|---|---|---|
| 1 | Agency name missing in all 561,580 FY2026 rows | A field dropped from the FY2026 export or publishing view | Schema check on every load: required columns must exist and be non-empty. Fail the load if not. Keep a change log of schema changes | R03 |
| 2 | 71,716 hourly rows with a rate of $2 or less (poll workers at $1.00) and 1,724 hourly rows with annual-sized rates (custodian engineers) | Flat-fee and salaried workers stored in an hourly-rate field to fit the format | Add a pay-type field (flat stipend, salaried, hourly) so a placeholder is not read as a wage. Validate rate range per pay basis | R14, R15 |
| 3 | 10,898 titles and 15,120 borough values with non-standard spelling or naming | Free-text entry at the agency | Use controlled lookup lists for title and borough instead of free text | R12, R13 |
| 4 | 999 rows with negative hours and 3,266 with negative pay | Reversals entered as negative amounts on the same record type | Store adjustments as a separate record type with a reason code | R08, R09 |
| 5 | 7,287 rows where overtime hours and overtime pay disagree | Hours and pay posted in different periods | Cross-field rule: overtime pay greater than 0 requires overtime hours greater than 0, with a documented exception list | R11 |
| 6 | 40 start dates of 9999-12-31 or in the future | A placeholder used instead of NULL | Reject placeholder dates. Use NULL for unknown | R07 |
| 7 | 2,084 people with a different start date in the two years | Corrections or rehires entered without history | Record start-date changes with an effective date and reason | Cross-year check |
| 8 | Warnings concentrate in a few agencies (for example one District Attorney office at 8.8% and Dept of Ed Pedagogical at 8.0% of FY2026 records) | Agency-level entry practices | Send each agency its own quality scorecard and agree a target | All |

## Proposed ongoing process
1. Run `python run_pipeline.py` after each new load (see docs/06_sop_quality_run.md).
2. Review the scorecard. Any rule that fails its threshold goes to the data owner with the example counts.
3. Track the pass rate over time. Today it is 13 of 15 rules (86.7%). The two failures are escalated (R11 overtime mismatch, R15 pay that cannot be annualized).
4. Keep the data dictionary and requirements in version control and update them when a rule changes.
