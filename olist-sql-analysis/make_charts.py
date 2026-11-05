"""Make the README charts from the query results saved in outputs/.

Run after the SQL files:  python make_charts.py
"""
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

HERE = Path(__file__).parent
OUT = HERE / "outputs"

BLUE, ORANGE = "#2a78d6", "#eb6834"
INK, MUTED, GRID = "#0b0b0b", "#52514e", "#e4e3df"

plt.rcParams.update({
    "font.family": "DejaVu Sans",
    "axes.edgecolor": GRID,
    "axes.labelcolor": MUTED,
    "xtick.color": MUTED,
    "ytick.color": MUTED,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "figure.dpi": 150,
})


def tidy(ax):
    ax.grid(axis="y", color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)


def review_by_delivery():
    df = pd.read_csv(OUT / "01_delivery_experience_3.csv")
    labels = [b[3:] for b in df["delivery_bucket"]]
    colors = [BLUE if "early" in l else ORANGE for l in labels]
    fig, ax = plt.subplots(figsize=(8, 4.2))
    bars = ax.bar(labels, df["avg_score"], color=colors, width=0.62)
    for b, v in zip(bars, df["avg_score"]):
        ax.text(b.get_x() + b.get_width() / 2, v + 0.06, f"{v:.2f}", ha="center", color=INK, fontsize=10)
    ax.set_ylim(0, 5)
    ax.set_ylabel("Average review score (1-5)")
    ax.set_title("Reviews drop sharply once an order arrives after the promised date",
                 loc="left", color=INK, fontsize=12, fontweight="bold")
    tidy(ax)
    fig.tight_layout()
    fig.savefig(OUT / "chart_review_by_delivery.png")
    plt.close(fig)


def monthly_revenue():
    df = pd.read_csv(OUT / "02_revenue_growth_1.csv")
    x = pd.to_datetime(df["month"])
    fig, ax = plt.subplots(figsize=(8, 4.2))
    ax.plot(x, df["revenue_brl"] / 1000, color=BLUE, linewidth=2)
    ax.scatter(x, df["revenue_brl"] / 1000, color=BLUE, s=22, zorder=3)
    peak = df["revenue_brl"].idxmax()
    nov = df[df["month"] == "2017-11"].index[0]
    ax.annotate(f"Nov 2017: {df['revenue_brl'][peak] / 1000:,.0f}k\nBlack Friday, 24 Nov: 1,176 orders in a day",
                (x[nov], df["revenue_brl"][nov] / 1000),
                xytext=(-215, -4), textcoords="offset points", color=INK, fontsize=9,
                arrowprops=dict(arrowstyle="-", color=MUTED))
    ax.set_ylabel("Monthly revenue (thousand BRL)")
    ax.set_ylim(0, 1100)
    ax.set_title("Revenue grew about 8x from Jan 2017 and then levelled off in 2018",
                 loc="left", color=INK, fontsize=12, fontweight="bold")
    tidy(ax)
    fig.autofmt_xdate()
    fig.tight_layout()
    fig.savefig(OUT / "chart_monthly_revenue.png")
    plt.close(fig)


def late_by_state():
    df = pd.read_csv(OUT / "01_delivery_experience_4.csv").sort_values("pct_late")
    fig, ax = plt.subplots(figsize=(8, 4.6))
    bars = ax.barh(df["state"], df["pct_late"], color=BLUE, height=0.62)
    for b, v in zip(bars, df["pct_late"]):
        ax.text(v + 0.2, b.get_y() + b.get_height() / 2, f"{v:.1f}%", va="center", color=INK, fontsize=9)
    ax.set_xlabel("Orders delivered late (%)")
    ax.set_xlim(0, df["pct_late"].max() + 2.5)
    ax.set_title("Ceara, Bahia and Rio de Janeiro have the highest late-delivery rates",
                 loc="left", color=INK, fontsize=12, fontweight="bold")
    ax.grid(axis="x", color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    fig.tight_layout()
    fig.savefig(OUT / "chart_late_by_state.png")
    plt.close(fig)


if __name__ == "__main__":
    review_by_delivery()
    monthly_revenue()
    late_by_state()
    print("Charts saved to", OUT)
