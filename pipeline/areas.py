"""Neighborhood areas and how flooding grows in each as the water rises.

Areas (simple lon/lat boxes; only land assets inside them are counted):
  Mission Beach   jetty -> Pacific Beach Dr. Ocean Front Walk, Bayside Walk,
                  Belmont Park, Santa Clara Point, El Carmel Point, Bahia.
  Pacific Beach   Pacific Beach Dr -> Tourmaline. Crystal Pier, beachfront,
                  Sail Bay north shore (Briarfield, Fanuel St Park).
  Crown Point     east side of Sail Bay: Crown Point, Riviera Shores.
(Campland and anything further east are outside the study area.)

For each area, at every Mission Bay still-water level from 6 to 11 ft
(0.05 ft steps), we count:
  buildings        water reaches the property (within 2 m of the building)
  drain_buildings  lower than the water but no surface path (storm-drain risk)
  road_mi          miles of street with the road covered
  walk_mi          miles of walkway reached (Bayside Walk, paths, ...)
Ocean side: the CDIP MOP beach stretches that belong to each area.

Outputs (data/processed/):
  areas.geojson      area outlines (for the map)
  area_curves.json   the counts above, per area and level, plus beach stretches

Usage:
  python pipeline/areas.py
"""

from __future__ import annotations

import json

import geopandas as gpd
import numpy as np
import pandas as pd
from shapely.geometry import box

from noaa_tides import PROCESSED_DIR, PROJECT_ROOT

AREAS = {
    # name: (west, south, east, north)
    "Mission Beach": (-117.2620, 32.7585, -117.2425, 32.7908),
    "Pacific Beach": (-117.2700, 32.7908, -117.2420, 32.8120),
    "Crown Point": (-117.2425, 32.7780, -117.2285, 32.8000),
}
OCEAN_FRONT = {"Mission Beach", "Pacific Beach"}  # areas with an open-ocean beach
LEVELS = np.round(np.arange(6.0, 11.0001, 0.05), 2)
# Things reached at or below this level get wet on ordinary high tides (beach
# paths, lifeguard stations on the sand). Mission Bay's normal high tide (MHHW)
# is 5.45 ft; we round up to 6.0 ft. They are left out of every count.
ROUTINELY_WET_FT = 6.0
M_PER_MI = 1609.34


def main() -> None:
    areas = gpd.GeoDataFrame({"name": list(AREAS)}, geometry=[box(*b) for b in AREAS.values()], crs="EPSG:4326")
    buildings = gpd.read_file(PROCESSED_DIR / "buildings_danger.geojson")
    streets = gpd.read_file(PROCESSED_DIR / "street_pieces_danger.geojson")
    profiles = pd.read_csv(PROCESSED_DIR / "shore_profiles.csv")

    # Assign each building / street piece to the area containing its center.
    b_area = gpd.sjoin(gpd.GeoDataFrame(buildings[["danger_bay_ft", "ground_min_ft"]],
                                        geometry=buildings.to_crs(26911).centroid.to_crs(4326)),
                       areas, predicate="within")
    s_area = gpd.sjoin(gpd.GeoDataFrame(streets[["kind", "length_m", "danger_bay_ft", "covered_bay_ft"]],
                                        geometry=streets.to_crs(26911).centroid.to_crs(4326)),
                       areas, predicate="within")

    curves = {"levels_ft_mllw": LEVELS.tolist(), "areas": {}}
    for name, (w, s, e, n) in AREAS.items():
        b = b_area[b_area.name == name]
        st = s_area[s_area.name == name]
        b = b[~(b.danger_bay_ft <= ROUTINELY_WET_FT)]
        st = st[~(st.danger_bay_ft <= ROUTINELY_WET_FT)]
        streets_only, walks = st[st.kind == "street"], st[st.kind == "walkway"]
        reached = lambda lv: int((b.danger_bay_ft <= lv).sum())
        drain = lambda lv: int(((b.danger_bay_ft > lv) & (b.ground_min_ft < lv)).sum())
        road = lambda lv: round(streets_only.loc[streets_only.covered_bay_ft <= lv, "length_m"].sum() / M_PER_MI, 3)
        walk = lambda lv: round(walks.loc[walks.danger_bay_ft <= lv, "length_m"].sum() / M_PER_MI, 3)
        beach = profiles[(profiles.lat >= s) & (profiles.lat < n)
                         & profiles.barrier.isin(["ridge", "rising ground"])] if name in OCEAN_FRONT else profiles[:0]
        curves["areas"][name] = {
            "total_buildings": int(len(b)),
            "buildings": [reached(lv) for lv in LEVELS],
            "drain_buildings": [drain(lv) for lv in LEVELS],
            "road_mi": [road(lv) for lv in LEVELS],
            "walk_mi": [walk(lv) for lv in LEVELS],
            "beach_points": beach.point.tolist(),
        }

    areas.to_file(PROCESSED_DIR / "areas.geojson", driver="GeoJSON")
    curves["notes"] = {
        "level": "Mission Bay still-water level, feet above MLLW (NOAA La Jolla datums)",
        "buildings": "water reaches ground within 2 m of the building (floor heights unknown)",
        "assignment": "assets assigned to the area containing their center",
        "routinely_wet": f"assets reached at or below {ROUTINELY_WET_FT} ft (ordinary high tides) are not counted",
    }
    (PROCESSED_DIR / "area_curves.json").write_text(json.dumps(curves))

    show = [7.0, 7.4, 7.8, 8.12, 8.5, 9.0]
    idx = [int(np.argmin(abs(LEVELS - lv))) for lv in show]
    for name, c in curves["areas"].items():
        print(f"\n{name}: {c['total_buildings']:,} buildings in area, {len(c['beach_points'])} beach stretches "
              f"({c['beach_points'][0] if c['beach_points'] else '-'}..{c['beach_points'][-1] if c['beach_points'] else '-'})")
        for lv, i in zip(show, idx):
            print(f"  {lv:5.2f} ft: {c['buildings'][i]:4d} buildings (+{c['drain_buildings'][i]} drain risk), "
                  f"{c['road_mi'][i]:.2f} mi road covered, {c['walk_mi'][i]:.2f} mi walkway")
    print(f"\nSaved areas.geojson and area_curves.json in {PROCESSED_DIR.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
