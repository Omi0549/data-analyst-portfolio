"""Build the Excel data quality scorecard from the validation results in outputs/.

Pass/fail and percentages are live Excel formulas, so a reviewer can change a threshold and see the status update.
Run after sql/03_validation.sql:  python build_scorecard.py
"""
import os

import pandas as pd
from openpyxl import Workbook
from openpyxl.formatting.rule import CellIsRule
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "outputs")

# What the pipeline does with each failing record. REMOVED / FIXED change data, the others do not.
ACTION = {
    "R01": "REMOVED: keep the first copy",
    "R02": "FLAGGED: kept, needs data owner review",
    "R03": "FIXED: rebuilt from payroll_number reference table",
    "R04": "FLAGGED: kept, names are not used in curated output",
    "R05": "FLAGGED: title set to UNKNOWN",
    "R06": "FLAGGED: borough set to UNKNOWN or OTHER/UNSPECIFIED",
    "R07": "FIXED: invalid date set to NULL and flagged",
    "R08": "QUARANTINED: excluded from report-ready rows",
    "R09": "QUARANTINED: excluded from report-ready rows",
    "R10": "QUARANTINED: excluded from report-ready rows",
    "R11": "ESCALATED: kept and flagged, cause unknown",
    "R12": "FIXED: upper-cased and spacing standardized",
    "R13": "FIXED: mapped RICHMOND to STATEN ISLAND",
    "R14": "QUARANTINED: pay basis likely wrong, confirm with data owner",
    "R15": "FLAGGED: annualized pay left blank, not guessed",
}
HEADER_FILL = PatternFill("solid", fgColor="1F3864")
HEADER_FONT = Font(bold=True, color="FFFFFF")


def style_header(ws, row=1):
    for cell in ws[row]:
        cell.fill, cell.font = HEADER_FILL, HEADER_FONT
        cell.alignment = Alignment(wrap_text=True, vertical="center")


def main():
    rules = pd.read_csv(os.path.join(OUT, "03_validation_1.csv"))
    recon = pd.read_csv(os.path.join(OUT, "03_validation_2.csv"))
    wb = Workbook()

    # Sheet 1: rule scorecard (formulas for percentages and status)
    ws = wb.active
    ws.title = "Rule Scorecard"
    ws.append(["Rule", "Requirement", "Description", "Raw failed", "Raw total", "Raw fail %",
               "Curated failed", "Curated total", "Curated fail %", "Threshold %", "Status", "Action taken"])
    for i, r in enumerate(rules.itertuples(), start=2):
        ws.append([r.rule_id, r.req_id, r.rule, r.raw_failed, r.raw_total, f"=D{i}/E{i}*100",
                   r.curated_failed, r.curated_total, f"=G{i}/H{i}*100", r.threshold_pct,
                   f'=IF(I{i}<=J{i},"PASS","FAIL")', ACTION[r.rule_id]])
        for col in ("D", "E", "G", "H"):
            ws[f"{col}{i}"].number_format = "#,##0"
        for col in ("F", "I", "J"):
            ws[f"{col}{i}"].number_format = "0.000"
    last = len(rules) + 1
    style_header(ws)
    ws.conditional_formatting.add(f"K2:K{last}", CellIsRule(operator="equal", formula=['"PASS"'], fill=PatternFill("solid", bgColor="C6EFCE")))
    ws.conditional_formatting.add(f"K2:K{last}", CellIsRule(operator="equal", formula=['"FAIL"'], fill=PatternFill("solid", bgColor="FFC7CE")))
    for col, width in zip("ABCDEFGHIJKL", (7, 12, 62, 13, 13, 11, 14, 14, 13, 11, 9, 52)):
        ws.column_dimensions[col].width = width
    ws.freeze_panes = "D2"

    # Sheet 2: summary KPIs (formulas reference the scorecard)
    s = wb.create_sheet("Summary", 0)
    total_raw, total_cur = int(recon["raw_rows"].sum()), int(recon["curated_rows"].sum())
    rows = [
        ("Metric", "Value"),
        ("Raw rows loaded (FY2025 + FY2026)", total_raw),
        ("Curated rows (after removing exact duplicates)", total_cur),
        ("Rows kept (%)", "=B3/B2*100"),
        ("Rules checked", f"=COUNTA('Rule Scorecard'!A2:A{last})"),
        ("Rules passing after cleaning", f"=COUNTIF('Rule Scorecard'!K2:K{last},\"PASS\")"),
        ("Rules failing after cleaning (escalate)", f"=COUNTIF('Rule Scorecard'!K2:K{last},\"FAIL\")"),
        ("Pass rate (%)", "=B6/B5*100"),
    ]
    for r in rows:
        s.append(r)
    style_header(s)
    for cell in ("B2", "B3"):
        s[cell].number_format = "#,##0"
    s["B4"].number_format = "0.000"
    s["B8"].number_format = "0.0"
    s.column_dimensions["A"].width = 52
    s.column_dimensions["B"].width = 16
    s["A10"] = "Thresholds are proposed targets for this case study. Change column J on the Rule Scorecard to see statuses update."
    s["A10"].font = Font(italic=True)

    # Sheet 3: reconciliation
    rc = wb.create_sheet("Reconciliation")
    rc.append(["Fiscal year", "Raw rows", "Exact duplicates removed", "Curated rows", "Ties out?"])
    for i, r in enumerate(recon.itertuples(), start=2):
        rc.append([r.fiscal_year, r.raw_rows, r.exact_duplicates_removed, r.curated_rows, f'=IF(B{i}-C{i}=D{i},"YES","NO")'])
        for col in "BCD":
            rc[f"{col}{i}"].number_format = "#,##0"
    style_header(rc)
    for col in "ABCDE":
        rc.column_dimensions[col].width = 24

    wb.properties.creator = "Om Biswal"
    wb.properties.title = "NYC payroll data quality scorecard"
    wb.save(os.path.join(OUT, "dq_scorecard.xlsx"))
    print("Saved", os.path.join(OUT, "dq_scorecard.xlsx"))


if __name__ == "__main__":
    main()
