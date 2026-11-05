"""Make the README charts from query results saved in outputs/.  Run after the SQL files: python make_charts.py"""
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

HERE = Path(__file__).parent
OUT = HERE / "outputs"

BLUE, ORANGE = "#2a78d6", "#eb6834"
INK, MUTED, GRID = "#0b0b0b", "#52514e", "#e4e3df"

plt.rcParams.update({
    "font.family": "DejaVu Sans", "axes.edgecolor": GRID, "axes.labelcolor": MUTED,
    "xtick.color": MUTED, "ytick.color": MUTED, "axes.spines.top": False,
    "axes.spines.right": False, "figure.dpi": 150,
})


def title(ax, text):
    ax.figure.suptitle(text, x=0.02, ha="left", color=INK, fontsize=12, fontweight="bold")


def issues_by_rule():
    df = pd.read_csv(OUT / "03_validation_1.csv")
    note = df[df["rule_id"] == "R03"].iloc[0]
    df = df[df["rule_id"] != "R03"].sort_values("raw_failed")
    short = {
        "R01": "Exact duplicate rows", "R02": "Possible duplicate appointment", "R04": "Name missing",
        "R05": "Job title missing", "R06": "Borough unknown or OTHER", "R07": "Invalid start date",
        "R08": "Negative hours", "R09": "Negative regular or OT pay", "R10": "Regular hours over 2,500",
        "R11": "OT hours and OT pay disagree", "R12": "Title spelled non-standard",
        "R13": "Borough name RICHMOND", "R14": "Hourly basis, annual-sized rate",
        "R15": "Pay cannot be annualized",
    }
    labels = [f"{r.rule_id}  {short[r.rule_id]}" for r in df.itertuples()]
    colors = [ORANGE if s == "FAIL" else BLUE for s in df["curated_status"]]
    fig, ax = plt.subplots(figsize=(9, 5.2))
    bars = ax.barh(labels, df["raw_failed"], color=colors, height=0.62)
    for b, v in zip(bars, df["raw_failed"]):
        ax.text(v + 600, b.get_y() + b.get_height() / 2, f"{v:,}", va="center", color=INK, fontsize=8)
    ax.set_xlabel("Records failing the rule before cleaning (1.11M rows)")
    ax.set_xlim(0, df["raw_failed"].max() * 1.15)
    ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{v:,.0f}"))
    fig.suptitle("Data quality issues found in raw NYC payroll data", x=0.02, ha="left",
                 color=INK, fontsize=12, fontweight="bold")
    ax.text(0.99, 0.02, f"Not shown: R03, agency name missing in all {int(note['raw_failed']):,} FY2026 rows (fixed)",
            transform=ax.transAxes, ha="right", fontsize=8, color=MUTED)
    ax.text(0.99, 0.08, "Orange = still failing after cleaning (escalated)", transform=ax.transAxes,
            ha="right", fontsize=8, color=ORANGE)
    ax.grid(axis="x", color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    fig.tight_layout()
    fig.savefig(OUT / "chart_dq_issues.png")
    plt.close(fig)


def agency_warnings():
    df = pd.read_csv(OUT / "04_analysis_6.csv").sort_values("pct_with_warning")
    fig, ax = plt.subplots(figsize=(9, 4.6))
    bars = ax.barh(df["agency_name"].str.title(), df["pct_with_warning"], color=BLUE, height=0.62)
    for b, v in zip(bars, df["pct_with_warning"]):
        ax.text(v + 0.1, b.get_y() + b.get_height() / 2, f"{v:.1f}%", va="center", color=INK, fontsize=9)
    ax.set_xlabel("Records with at least one data quality warning, FY2026 (%)")
    ax.set_xlim(0, df["pct_with_warning"].max() + 1.5)
    title(ax, "Where to fix data at the source: agencies with the most flagged records")
    ax.grid(axis="x", color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    fig.tight_layout()
    fig.savefig(OUT / "chart_agency_warnings.png")
    plt.close(fig)


def pay_by_borough():
    df = pd.read_csv(OUT / "04_analysis_5.csv").sort_values("median_annual_base")
    fig, ax = plt.subplots(figsize=(8, 3.8))
    bars = ax.barh(df["work_borough"].str.title(), df["median_annual_base"] / 1000, color=BLUE, height=0.6)
    for b, v in zip(bars, df["median_annual_base"]):
        ax.text(b.get_width() + 1, b.get_y() + b.get_height() / 2, f"${v:,.0f}", va="center", color=INK, fontsize=9)
    ax.set_xlabel("Median annual base pay (thousand USD), salaried employees, FY2026")
    ax.set_xlim(0, df["median_annual_base"].max() / 1000 * 1.18)
    title(ax, "Median salary is highest for Manhattan-based employees")
    ax.grid(axis="x", color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    fig.tight_layout()
    fig.savefig(OUT / "chart_pay_by_borough.png")
    plt.close(fig)


def main():
    issues_by_rule()
    agency_warnings()
    pay_by_borough()
    print("Charts saved to", OUT)


if __name__ == "__main__":
    main()
