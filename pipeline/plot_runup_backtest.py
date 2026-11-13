"""Chart: how close did the waves get to the top of the beach ridge / boardwalk?

For each backtest event, the worst moment at each ~100 m stretch of beach,
from the Mission Beach jetty (left) to Pacific Beach (right).
  y > 0  water over the top
  0 to -2  waves reach the top (splash / spray / some water on the boardwalk)
  < -2  clear

Reads data/processed/runup/twl_*_archive.csv made by runup.py.

Usage:
  python pipeline/plot_runup_backtest.py
"""

from __future__ import annotations

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from noaa_tides import PROCESSED_DIR, PROJECT_ROOT

FIGURES_DIR = PROJECT_ROOT / "figures"
SURFACE, TEXT, TEXT_MUTED, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#e6e5e1"
# (file, local days to include, label, color) - fixed categorical order
EVENTS = [
    ("twl_2023-01-05_2023-01-07_archive.csv", ["2023-01-06"], "Jan 6, 2023 (boardwalk flooded)", "#2a78d6"),
    ("twl_2023-12-27_2023-12-31_archive.csv", ["2023-12-29", "2023-12-30"], "Dec 29–30, 2023 (boardwalk flooded)", "#eb6834"),
    ("twl_2024-01-03_2024-01-05_archive.csv", ["2024-01-04"], "Jan 4, 2024 (big surf, low tide; no flooding found)", "#1baf7a"),
    ("twl_2026-10-25_2026-10-28_archive.csv", ["2026-10-26"], "Oct 26, 2026 (small surf; bay-side flooding only)", "#eda100"),
]


def main() -> None:
    profiles = pd.read_csv(PROCESSED_DIR / "shore_profiles.csv").set_index("point")
    ridge = profiles[(profiles.barrier == "ridge") & (profiles.crest_ft < 20)].index  # low-lying stretches
    order = {p: i for i, p in enumerate(sorted(ridge))}

    plt.rcParams.update({"font.family": "Helvetica Neue", "font.size": 10, "text.color": TEXT,
                         "axes.edgecolor": GRID, "axes.labelcolor": TEXT_MUTED, "xtick.color": TEXT_MUTED,
                         "ytick.color": TEXT_MUTED, "axes.spines.top": False, "axes.spines.right": False,
                         "axes.spines.left": False})
    fig, ax = plt.subplots(figsize=(12, 5.6))
    fig.patch.set_facecolor(SURFACE); ax.set_facecolor(SURFACE)
    ax.axhspan(0, 3, color="#f6d5d5", lw=0, zorder=0)
    ax.axhspan(-2, 0, color="#fbe9c7", lw=0, zorder=0)
    ax.text(len(order) - 0.5, 1.5, "Water over the top", ha="right", va="center", fontsize=9, color=TEXT_MUTED)
    ax.text(len(order) - 0.5, -1.0, "Waves reach the top", ha="right", va="center", fontsize=9, color=TEXT_MUTED)
    ax.text(len(order) - 0.5, -8.4, "Clear", ha="right", va="center", fontsize=9, color=TEXT_MUTED)

    for fname, days, label, color in EVENTS:
        t = pd.read_csv(PROCESSED_DIR / "runup" / fname, parse_dates=["time_utc"])
        t = t[t.point.isin(order)]
        t = t[t.time_utc.dt.tz_convert("America/Los_Angeles").dt.strftime("%Y-%m-%d").isin(days)]
        worst = t.groupby("point").margin_ft.min()
        x = np.array([order[p] for p in worst.index]); y = -worst.to_numpy()
        ax.plot(x, y, color=color, lw=2, label=label, marker="o", ms=3.5, markeredgecolor=SURFACE)

    ticks = {"D0365": "Jetty", "D0377": "Belmont\nPark", "D0390": "N. Mission\nBeach", "D0398": "Pacific\nBeach Dr",
             "D0411": "Crystal\nPier"}
    ax.set_xticks([order[p] for p in ticks if p in order], [v for p, v in ticks.items() if p in order])
    ax.set_ylim(-9, 3)
    ax.set_ylabel("Highest wave water level minus\nridge / boardwalk top (ft)")
    ax.grid(axis="y", color=GRID, lw=0.8)
    ax.tick_params(length=0)
    ax.legend(loc="lower left", frameon=True, facecolor="white", edgecolor="none", fontsize=9, framealpha=0.95)
    ax.set_title("Backtest: did the model call wave flooding on the right days?", loc="left",
                 fontsize=13, fontweight="bold", pad=10)
    fig.text(0.01, -0.02,
             "Each point = one ~100 m stretch of beach (CDIP MOP point), worst hour of the day. Water level = measured "
             "La Jolla tide + Stockdon (2006) R2 run-up from CDIP MOP waves.\nRidge / boardwalk top from USGS 2024 lidar. "
             "Bluff stretches (PB north of Crystal Pier) are omitted - water can't get over them.",
             fontsize=8, color=TEXT_MUTED, va="top")
    FIGURES_DIR.mkdir(exist_ok=True)
    out = FIGURES_DIR / "runup_backtest.png"
    fig.savefig(out, dpi=160, bbox_inches="tight", facecolor=SURFACE)
    print(f"Saved {out.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
