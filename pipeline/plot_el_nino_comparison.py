"""Compare this winter's extra water with past big El Ninos.

Reads data/processed/monthly_extra_water_<station>.csv (made by noaa_history.py)
and draws two charts in figures/:

  el_nino_comparison_<station>.png  Each El Nino winter as one line, June -> May,
                                    over a gray band showing the normal range.
  extra_water_history_<station>.png Every month since 1980, so you can see the
                                    big events stand out from 46 years of normal.

Values are the ANOMALY: monthly extra water minus the slow sea-level-rise
baseline, i.e. the part caused by El Nino / Kelvin waves / storms.

Usage:
  python pipeline/plot_el_nino_comparison.py            # San Diego
  python pipeline/plot_el_nino_comparison.py --station 9410230
"""

from __future__ import annotations

import argparse
import json

import matplotlib

matplotlib.use("Agg")
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from noaa_tides import PROCESSED_DIR, PROJECT_ROOT

FIGURES_DIR = PROJECT_ROOT / "figures"

SURFACE = "#fcfcfb"
TEXT = "#0b0b0b"
TEXT_MUTED = "#52514e"
GRID = "#e6e5e1"
NORMAL_BAND = "#e3e2dd"
# Fixed categorical order (validated palette, light mode). Current winter first.
WINTERS = [
    ("2026-27", "#2a78d6", "This winter"),
    ("2015-16", "#eb6834", "2015–16"),
    ("1997-98", "#1baf7a", "1997–98"),
    ("1982-83", "#eda100", "1982–83"),
]
SEASON_MONTHS = ["Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec", "Jan", "Feb", "Mar", "Apr", "May"]


def style() -> None:
    plt.rcParams.update({
        "font.family": "Helvetica Neue", "font.size": 10, "text.color": TEXT,
        "axes.edgecolor": GRID, "axes.labelcolor": TEXT_MUTED,
        "xtick.color": TEXT_MUTED, "ytick.color": TEXT_MUTED,
        "axes.spines.top": False, "axes.spines.right": False, "axes.spines.left": False,
    })


def season_view(monthly: pd.DataFrame) -> pd.DataFrame:
    """Reshape to one row per season (June->May), one column per month 0..11."""
    df = monthly[["anomaly_ft"]].copy()
    df["season_start"] = np.where(df.index.month >= 6, df.index.year, df.index.year - 1)
    df["season_month"] = (df.index.month - 6) % 12
    return df.pivot(index="season_start", columns="season_month", values="anomaly_ft")


def plot_comparison(monthly: pd.DataFrame, meta: dict, out_name: str) -> None:
    seasons = season_view(monthly)
    el_nino_starts = {int(name[:4]) for name, _, _ in WINTERS}
    normal = seasons.drop(index=[s for s in el_nino_starts if s in seasons.index])
    lo, hi = normal.quantile(0.10), normal.quantile(0.90)

    fig, ax = plt.subplots(figsize=(11, 6.2))
    fig.patch.set_facecolor(SURFACE)
    ax.set_facecolor(SURFACE)
    x = np.arange(12)

    ax.fill_between(x, lo, hi, color=NORMAL_BAND, lw=0, zorder=1)
    ax.text(5, (lo[5] + hi[5]) / 2 - 0.05, "Normal range (80% of other years)",
            color=TEXT_MUTED, fontsize=9, ha="center", va="center", zorder=2)
    ax.axhline(0, color=TEXT_MUTED, lw=0.8, zorder=2)

    # Draw past winters first, this winter last (on top).
    end_labels = []  # (y, label, x, is_current) for past winters' right-edge labels
    for name, color, label in reversed(WINTERS):
        start = int(name[:4])
        if start not in seasons.index:
            continue
        y = seasons.loc[start]
        is_current = name == WINTERS[0][0]
        ax.plot(x, y, color=color, lw=3 if is_current else 1.8, zorder=4 if is_current else 3,
                marker="o", ms=5 if is_current else 0, markeredgecolor=SURFACE, markeredgewidth=1.5)
        last = y.last_valid_index()
        if is_current:
            so_far = f"  ({monthly.index[-1]:%b} so far)" if monthly["partial"].iloc[-1] else ""
            ax.annotate(f"{label}  {y[last]:+.2f} ft{so_far}", xy=(last, y[last]), xytext=(8, 0),
                        textcoords="offset points", color=TEXT, fontsize=10, fontweight="bold", va="center")
        else:
            end_labels.append([y[last], label, last])

    # Nudge right-edge labels apart so they never overlap (min gap in data units).
    end_labels.sort()
    min_gap = 0.045
    for i in range(1, len(end_labels)):
        end_labels[i][0] = max(end_labels[i][0], end_labels[i - 1][0] + min_gap)
    for y_label, label, last in end_labels:
        ax.text(last + 0.15, y_label, label, color=TEXT, fontsize=9, va="center")

    ax.set_xticks(x, SEASON_MONTHS)
    ax.set_xlim(-0.3, 12.6)
    ax.set_ylabel("Extra water above normal (ft, monthly average)")
    ax.grid(axis="y", color=GRID, lw=0.8)
    ax.tick_params(length=0)
    ax.set_title(f"{meta['station_name']}: this winter vs. the biggest El Niños on record",
                 loc="left", fontsize=13, fontweight="bold", pad=10)
    fig.text(0.01, -0.02,
             "“Extra water above normal” = measured − predicted tide, minus the slow sea-level-rise trend "
             f"({meta['baseline']['slope_ft_per_decade']:+.2f} ft/decade).\n"
             f"Source: NOAA CO-OPS station {meta['station']}, hourly data 1980–{meta['end_date'][:4]}, "
             f"downloaded {meta['downloaded_at_utc'][:10]}. Recent months are preliminary.",
             fontsize=8, color=TEXT_MUTED, va="top")
    save(fig, out_name)


def plot_history(monthly: pd.DataFrame, meta: dict, out_name: str) -> None:
    fig, ax = plt.subplots(figsize=(12, 4.8))
    fig.patch.set_facecolor(SURFACE)
    ax.set_facecolor(SURFACE)
    y = monthly["anomaly_ft"]
    ax.axhline(0, color=TEXT_MUTED, lw=0.8)
    ax.plot(y.index, y, color="#2a78d6", lw=1.2)

    for name, _, label in WINTERS:
        winter = monthly.loc[monthly["el_nino_winter"] == name, "anomaly_ft"].dropna()
        if winter.empty:
            continue
        peak = winter.idxmax()
        ax.scatter([peak], [winter.max()], s=36, color="#2a78d6", edgecolor=SURFACE, lw=1.5, zorder=4)
        ax.annotate(f"{label}\n{winter.max():+.2f} ft", xy=(peak, winter.max()), xytext=(0, 8),
                    textcoords="offset points", ha="right" if name == WINTERS[0][0] else "center",
                    va="bottom", fontsize=9, color=TEXT)

    ax.set_ylabel("Extra water above normal (ft)")
    ax.set_ylim(top=y.max() + 0.35)
    ax.grid(axis="y", color=GRID, lw=0.8)
    ax.tick_params(length=0)
    ax.xaxis.set_major_locator(mdates.YearLocator(5))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    ax.set_title(f"{meta['station_name']}: extra water above normal, every month since 1980",
                 loc="left", fontsize=13, fontweight="bold", pad=10)
    fig.text(0.01, -0.02,
             f"Monthly average of measured − predicted tide, minus the sea-level-rise trend. "
             f"Source: NOAA CO-OPS station {meta['station']}, downloaded {meta['downloaded_at_utc'][:10]}.",
             fontsize=8, color=TEXT_MUTED, va="top")
    save(fig, out_name)


def save(fig: plt.Figure, name: str) -> None:
    FIGURES_DIR.mkdir(exist_ok=True)
    out = FIGURES_DIR / name
    fig.savefig(out, dpi=160, bbox_inches="tight", facecolor=SURFACE)
    plt.close(fig)
    print(f"Saved {out.relative_to(PROJECT_ROOT)}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--station", default="9410170")
    args = parser.parse_args()

    monthly = pd.read_csv(PROCESSED_DIR / f"monthly_extra_water_{args.station}.csv",
                          index_col="month", parse_dates=["month"], keep_default_na=False,
                          na_values=[""], dtype={"el_nino_winter": str})
    monthly["el_nino_winter"] = monthly["el_nino_winter"].fillna("")
    monthly["partial"] = monthly["partial"].astype(str) == "True"
    meta = json.loads((PROCESSED_DIR / f"monthly_extra_water_{args.station}.meta.json").read_text())

    style()
    plot_comparison(monthly, meta, f"el_nino_comparison_{args.station}.png")
    plot_history(monthly, meta, f"extra_water_history_{args.station}.png")


if __name__ == "__main__":
    main()
