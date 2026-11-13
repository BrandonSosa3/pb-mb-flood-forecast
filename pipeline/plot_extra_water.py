"""Chart a water-level CSV made by noaa_tides.py.

Top panel:    measured water level vs. predicted tide.
Bottom panel: extra water (measured - predicted), raw and as a 25-hour average.
              The 25-hour average smooths out the tide cycle (a tidal day is
              ~24.8 h), leaving the slow "the whole ocean is higher" signal.

Usage:
  python pipeline/plot_extra_water.py data/processed/water_levels_9410170_20260929_20261113.csv
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # draw straight to a file, no window
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
FIGURES_DIR = PROJECT_ROOT / "figures"

# Colors (validated reference palette, light mode)
SURFACE = "#fcfcfb"
TEXT = "#0b0b0b"
TEXT_MUTED = "#52514e"
GRID = "#e6e5e1"
MEASURED = "#2a78d6"   # blue
PREDICTED = "#8a8984"  # neutral gray: the "baseline" the ocean is compared against
EXTRA = "#eb6834"      # orange


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("csv", type=Path)
    args = parser.parse_args()

    meta = json.loads(args.csv.with_suffix(".meta.json").read_text())
    df = pd.read_csv(args.csv, index_col="time_utc", parse_dates=["time_utc"])
    df.index = df.index.tz_convert("America/Los_Angeles")
    extra_25h = df["extra_water_ft"].rolling("25h", center=True, min_periods=200).mean()

    plt.rcParams.update({
        "font.family": "Helvetica Neue", "font.size": 10, "text.color": TEXT,
        "axes.edgecolor": GRID, "axes.labelcolor": TEXT_MUTED,
        "xtick.color": TEXT_MUTED, "ytick.color": TEXT_MUTED,
        "axes.spines.top": False, "axes.spines.right": False,
    })
    fig, (top, bottom) = plt.subplots(
        2, 1, figsize=(12, 7.5), sharex=True, gridspec_kw={"height_ratios": [3, 2], "hspace": 0.12}
    )
    fig.patch.set_facecolor(SURFACE)

    # --- Top: measured vs predicted ---
    top.plot(df.index, df["predicted_ft"], color=PREDICTED, lw=1.2, label="Predicted tide (moon + sun only)")
    top.plot(df.index, df["observed_ft"], color=MEASURED, lw=1.2, label="Measured water level")
    peak_time = df["observed_ft"].idxmax()
    peak = df.loc[peak_time]
    top.scatter([peak_time], [peak["observed_ft"]], s=40, color=MEASURED, edgecolor=SURFACE, lw=2, zorder=5)
    top.annotate(
        f"{peak['observed_ft']:.2f} ft  ·  {peak_time:%b %d, %-I:%M %p}\n"
        f"{peak['extra_water_ft']:+.2f} ft above prediction",
        xy=(peak_time, peak["observed_ft"]), xytext=(-10, 0), textcoords="offset points",
        fontsize=9, color=TEXT, ha="right", va="center",
        bbox={"boxstyle": "round,pad=0.35", "facecolor": SURFACE, "edgecolor": GRID},
    )
    top.set_ylim(top=peak["observed_ft"] + 0.6)
    top.set_ylabel("Water level (ft above MLLW)")
    top.legend(loc="lower left", frameon=False, ncols=2)
    top.set_title(
        f"{meta['station_name']} — measured vs. predicted water level",
        loc="left", fontsize=13, fontweight="bold", pad=10,
    )

    # --- Bottom: extra water ---
    bottom.axhline(0, color=TEXT_MUTED, lw=0.8)
    bottom.plot(df.index, df["extra_water_ft"], color=EXTRA, lw=0.8, alpha=0.35, label="Every 6 minutes")
    bottom.plot(extra_25h.index, extra_25h, color=EXTRA, lw=2.2, label="25-hour average")
    bottom.set_ylabel("Extra water (ft)")
    bottom.legend(loc="lower left", frameon=False, ncols=2)
    bottom.set_title("Extra water = measured − predicted", loc="left", fontsize=11, fontweight="bold", pad=6)

    for ax in (top, bottom):
        ax.set_facecolor(SURFACE)
        ax.grid(axis="y", color=GRID, lw=0.8)
        ax.tick_params(length=0)
    bottom.xaxis.set_major_locator(mdates.WeekdayLocator(byweekday=mdates.MO))
    bottom.xaxis.set_major_formatter(mdates.DateFormatter("%b %d"))

    fig.text(
        0.01, 0.005,
        f"Source: NOAA CO-OPS, station {meta['station']}, 6-minute data, downloaded "
        f"{meta['downloaded_at_utc'][:10]}. Recent data is preliminary. Times are San Diego local.",
        fontsize=8, color=TEXT_MUTED,
    )

    FIGURES_DIR.mkdir(exist_ok=True)
    out = FIGURES_DIR / (args.csv.stem.replace("water_levels", "extra_water") + ".png")
    fig.savefig(out, dpi=160, bbox_inches="tight", facecolor=SURFACE)
    print(f"Saved {out.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
