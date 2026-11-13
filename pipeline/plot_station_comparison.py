"""Check that two tide gauges tell the same story.

San Diego (9410170) sits inside San Diego Bay; La Jolla (9410230) is on the
open coast near Pacific Beach. If the extra-water signal is real ocean-wide
water (El Nino / Kelvin wave) and not something local to the bay, the two
gauges should move together.

Reads the monthly CSVs made by noaa_history.py and saves
figures/station_comparison.png. Prints the agreement statistics.

Usage:
  python pipeline/plot_station_comparison.py
"""

from __future__ import annotations

import json

import matplotlib

matplotlib.use("Agg")
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import pandas as pd

from noaa_tides import PROCESSED_DIR, PROJECT_ROOT, STATIONS

FIGURES_DIR = PROJECT_ROOT / "figures"
SURFACE, TEXT, TEXT_MUTED, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#e6e5e1"
SERIES = [("9410230", "#2a78d6"), ("9410170", "#eb6834")]  # La Jolla first (closest to PB)


def load(station: str) -> pd.Series:
    df = pd.read_csv(PROCESSED_DIR / f"monthly_extra_water_{station}.csv", index_col="month", parse_dates=["month"])
    return df["anomaly_ft"]


def main() -> None:
    data = pd.concat({s: load(s) for s, _ in SERIES}, axis=1)
    both = data.dropna()
    corr = both.corr().iloc[0, 1]
    median_diff = (both.iloc[:, 0] - both.iloc[:, 1]).abs().median()
    print(f"Months with both gauges: {len(both)}")
    print(f"Correlation: {corr:.3f}   Typical (median) difference: {median_diff:.3f} ft")

    plt.rcParams.update({
        "font.family": "Helvetica Neue", "font.size": 10, "text.color": TEXT,
        "axes.edgecolor": GRID, "axes.labelcolor": TEXT_MUTED,
        "xtick.color": TEXT_MUTED, "ytick.color": TEXT_MUTED,
        "axes.spines.top": False, "axes.spines.right": False, "axes.spines.left": False,
    })
    fig, ax = plt.subplots(figsize=(12, 4.8))
    fig.patch.set_facecolor(SURFACE)
    ax.set_facecolor(SURFACE)
    ax.axhline(0, color=TEXT_MUTED, lw=0.8)

    for station, color in SERIES:
        y = data[station]
        name = STATIONS[station]
        ax.plot(y.index, y, color=color, lw=1.2, label=name)
        last = y.last_valid_index()
        ax.scatter([last], [y[last]], s=36, color=color, edgecolor=SURFACE, lw=1.5, zorder=4)

    # Direct labels for the two current values, nudged apart.
    ends = sorted((data[s].dropna().iloc[-1], s) for s, _ in SERIES)
    if ends[1][0] - ends[0][0] < 0.08:
        ends[1] = (ends[0][0] + 0.08, ends[1][1])
    for y_val, station in ends:
        ax.annotate(f"{STATIONS[station].split(' (')[0]} {data[station].dropna().iloc[-1]:+.2f} ft",
                    xy=(data.index[-1], y_val), xytext=(8, 0), textcoords="offset points",
                    va="center", fontsize=9, color=TEXT)

    ax.legend(loc="lower left", frameon=False, ncols=2)
    ax.set_ylabel("Extra water above normal (ft)")
    ax.grid(axis="y", color=GRID, lw=0.8)
    ax.tick_params(length=0)
    ax.xaxis.set_major_locator(mdates.YearLocator(5))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    ax.set_title("Open coast (La Jolla) and bay (San Diego) gauges move together",
                 loc="left", fontsize=13, fontweight="bold", pad=10)
    meta = json.loads((PROCESSED_DIR / "monthly_extra_water_9410230.meta.json").read_text())
    fig.text(0.01, -0.02,
             f"Monthly extra water above normal. Correlation {corr:.2f} over {len(both)} months; "
             f"typical difference {median_diff:.2f} ft. Source: NOAA CO-OPS stations 9410230 and 9410170, "
             f"downloaded {meta['downloaded_at_utc'][:10]}.",
             fontsize=8, color=TEXT_MUTED, va="top")

    FIGURES_DIR.mkdir(exist_ok=True)
    out = FIGURES_DIR / "station_comparison.png"
    fig.savefig(out, dpi=160, bbox_inches="tight", facecolor=SURFACE)
    print(f"Saved {out.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
