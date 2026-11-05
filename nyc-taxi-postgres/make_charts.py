"""Make the README charts from the query results saved in outputs/.

Run after the SQL files:  python make_charts.py
"""
from pathlib import Path

import matplotlib.dates as mdates
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


def title(ax, text):
    ax.set_title(text, loc="left", color=INK, fontsize=12, fontweight="bold")


def demand_by_hour():
    df = pd.read_csv(OUT / "02_analysis_1.csv")
    fig, ax = plt.subplots(figsize=(8, 4.2))
    for day_type, color in (("weekday", BLUE), ("weekend", ORANGE)):
        g = df[df["day_type"] == day_type]
        ax.plot(g["pickup_hour"], g["avg_trips_per_hour"], color=color, linewidth=2, label=day_type.capitalize())
        top = g.loc[g["avg_trips_per_hour"].idxmax()]
        ax.annotate(f"{top['avg_trips_per_hour']:,.0f} at {int(top['pickup_hour'])}:00",
                    (top["pickup_hour"], top["avg_trips_per_hour"]), xytext=(0, 8),
                    textcoords="offset points", ha="center", color=color, fontsize=9)
    ax.set_xticks(range(0, 24, 3))
    ax.set_xlabel("Pickup hour of day")
    ax.set_ylabel("Average trips per hour")
    ax.set_ylim(0, 8000)
    ax.legend(frameon=False, loc="upper left")
    title(ax, "Weekday demand peaks at 9 pm; weekends peak at 6 pm")
    tidy(ax)
    fig.tight_layout()
    fig.savefig(OUT / "chart_demand_by_hour.png")
    plt.close(fig)


def daily_trips():
    df = pd.read_csv(OUT / "02_analysis_6.csv", parse_dates=["pickup_date"])
    fig, ax = plt.subplots(figsize=(8, 4.2))
    ax.plot(df["pickup_date"], df["trips"] / 1000, color=GRID, linewidth=1.2, label="Daily trips")
    ax.plot(df["pickup_date"], df["trips_7day_avg"] / 1000, color=BLUE, linewidth=2.2, label="7-day average")
    ax.set_ylabel("Trips per day (thousands)")
    ax.set_ylim(0, 160)
    ax.legend(frameon=False, loc="lower right")
    title(ax, "Trips per day: August was the quietest month and September the busiest")
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %d"))
    tidy(ax)
    fig.tight_layout()
    fig.savefig(OUT / "chart_daily_trips.png")
    plt.close(fig)


def manhattan_speed():
    df = pd.read_csv(OUT / "02_analysis_8.csv")
    fig, ax = plt.subplots(figsize=(8, 4.2))
    ax.bar(df["pickup_hour"], df["avg_mph"], color=BLUE, width=0.7)
    slow = df.loc[df["avg_mph"].idxmin()]
    ax.annotate(f"Slowest: {slow['avg_mph']:.1f} mph at {int(slow['pickup_hour'])}:00",
                (slow["pickup_hour"], slow["avg_mph"]), xytext=(0, 14), textcoords="offset points",
                ha="center", color=INK, fontsize=9, arrowprops=dict(arrowstyle="-", color=MUTED))
    ax.set_xticks(range(0, 24, 3))
    ax.set_xlabel("Pickup hour of day")
    ax.set_ylabel("Average speed (mph)")
    title(ax, "Manhattan trips are slowest in the middle of the day")
    tidy(ax)
    fig.tight_layout()
    fig.savefig(OUT / "chart_manhattan_speed.png")
    plt.close(fig)


if __name__ == "__main__":
    demand_by_hour()
    daily_trips()
    manhattan_speed()
    print("Charts saved to", OUT)
