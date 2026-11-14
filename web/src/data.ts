// Types for the files the Python pipeline writes to public/data, plus small
// helpers that turn model output into plain language for the screens.

export const RISK_LEVELS = ["Low", "Minor", "Moderate", "Major"] as const;
export type Risk = (typeof RISK_LEVELS)[number];

export interface PlaceToWatch {
  point: string;
  near: string;
  margin_ft: number;
  over: boolean;
  lon: number;
  lat: number;
}

export interface ForecastDay {
  date: string; // YYYY-MM-DD, San Diego local
  risk: Risk;
  could_reach: Risk;
  risk_if_berm_fails: Risk;
  cause: "none" | "bay" | "ocean" | "both";
  worst_time: string | null;
  bay_peak_ft: number;
  bay_peak_time: string;
  berm_overtopped: boolean;
  properties_below_water: number;
  properties_reached: number;
  properties_if_berm_fails: number;
  stretches_reach_top: number | null;
  stretches_over: number | null;
  stretches_reach_top_upper: number;
  wave_height_ft: [number, number] | null;
  wave_period_s: [number, number] | null;
  /** Estimated set size as waves break: [typical stretch, biggest stretch], feet. */
  surf_ft?: [number, number] | null;
  /** NWS Surf Zone Forecast text for San Diego County beaches, when it covers this day. */
  nws_surf?: string | null;
  places_to_watch: PlaceToWatch[];
  /** Every beach stretch's closest call: [ft below the boardwalk top (negative = over), local time]. */
  stretches?: Record<string, [number, string]>;
}

export interface AreaForecast {
  name: string;
  days: ForecastDay[];
}

export interface NwsAlert {
  event: string;
  headline: string;
  ends: string | null;
  expires: string | null;
}

export interface Forecast {
  issued_at: string;
  extra_water_ft: number | null;
  nws_alerts: NwsAlert[];
  areas: AreaForecast[];
}

export async function loadForecast(): Promise<Forecast> {
  const res = await fetch("/data/forecast.json", { cache: "no-cache" });
  if (!res.ok) throw new Error(`forecast.json: ${res.status}`);
  return res.json();
}

// ---------- helpers ----------

export const riskIndex = (r: Risk) => RISK_LEVELS.indexOf(r);
export const worse = (a: Risk, b: Risk): Risk => (riskIndex(a) >= riskIndex(b) ? a : b);

export function slug(name: string) {
  return name.toLowerCase().replace(/[^a-z0-9]+/g, "-");
}

/** Days from today (San Diego time) onward, so a forecast made last night doesn't show yesterday. */
export function upcoming(days: ForecastDay[], now = new Date()): ForecastDay[] {
  const today = now.toLocaleDateString("en-CA", { timeZone: "America/Los_Angeles" });
  return days.filter((d) => d.date >= today);
}

/** The day to headline for an area: its worst upcoming day (earliest if tied). */
export function headlineDay(days: ForecastDay[]): ForecastDay | undefined {
  return days.reduce<ForecastDay | undefined>(
    (best, d) => (!best || riskIndex(d.risk) > riskIndex(best.risk) ? d : best),
    undefined,
  );
}

const TZ = "America/Los_Angeles";

export function dayLabel(date: string, now = new Date()): string {
  const today = now.toLocaleDateString("en-CA", { timeZone: TZ });
  if (date === today) return "Today";
  return new Date(`${date}T12:00:00`).toLocaleDateString("en-US", { weekday: "short" });
}

export function timeLabel(iso: string): string {
  const d = new Date(iso);
  // Round to the nearest hour: a forecast is not precise to the minute.
  d.setMinutes(d.getMinutes() + 30, 0, 0);
  return d.toLocaleTimeString("en-US", { hour: "numeric", timeZone: TZ }).replace(" AM", " am").replace(" PM", " pm");
}

export function updatedLabel(iso: string): string {
  const d = new Date(iso);
  const day = d.toLocaleDateString("en-US", { weekday: "short", month: "short", day: "numeric", timeZone: TZ });
  const time = d.toLocaleTimeString("en-US", { hour: "numeric", minute: "2-digit", timeZone: TZ });
  return `${day} · ${time.replace(" AM", " am").replace(" PM", " pm")}`;
}

/** One plain-language sentence for an area-day. No jargon. */
export function summary(day: ForecastDay): string {
  if (day.risk === "Low") return "No flooding expected.";
  const parts: string[] = [];
  const ocean = day.cause === "ocean" || day.cause === "both";
  const bay = day.cause === "bay" || day.cause === "both";
  if (ocean) {
    if ((day.stretches_over ?? 0) >= 3) parts.push("Waves are likely to wash over the boardwalk into nearby streets.");
    else if ((day.stretches_over ?? 0) > 0) parts.push("Waves may wash over the boardwalk in a few places.");
    else parts.push("Big surf at high tide. Waves may splash up onto the boardwalk.");
  }
  if (bay) {
    if (day.properties_reached >= 25) parts.push("Bay water likely in streets near the bay.");
    else if (day.properties_below_water >= 25) parts.push("High bay tide: storm drains may back up into low streets.");
    else parts.push("Bay water may cover parts of the bayside paths.");
  }
  return parts.join(" ");
}

export const NWS_URL = "https://www.weather.gov/sgx/";

// ---------- slider counts (area_curves.json) ----------

export interface AreaCurve {
  buildings: number[]; drain_buildings: number[]; road_mi: number[]; walk_mi: number[];
  buildings_berm: number[]; drain_buildings_berm: number[]; road_mi_berm: number[]; walk_mi_berm: number[];
}
export interface Curves { levels_ft_mllw: number[]; areas: Record<string, AreaCurve> }

export async function loadCurves(): Promise<Curves> {
  const res = await fetch("/data/area_curves.json");
  if (!res.ok) throw new Error(`area_curves.json: ${res.status}`);
  return res.json();
}

export const BERM_TOP_FT = 9.0; // must match pipeline/risk.py (an estimate)

/** Totals over all areas at a water level. Above the berm top the berm no longer matters. */
export function countsAt(curves: Curves, level: number, bermHolds: boolean) {
  const lv = curves.levels_ft_mllw;
  let i = lv.findIndex((x) => x > level + 1e-6) - 1;
  if (i < -1) i = lv.length - 1;
  const useBerm = bermHolds && level < BERM_TOP_FT;
  const total = { reached: 0, belowWater: 0, roadMi: 0, walkMi: 0 };
  if (i < 0) return { ...total, useBerm };
  for (const a of Object.values(curves.areas)) {
    total.reached += useBerm ? a.buildings_berm[i] : a.buildings[i];
    total.belowWater += useBerm ? a.drain_buildings_berm[i] : a.drain_buildings[i];
    total.roadMi += useBerm ? a.road_mi_berm[i] : a.road_mi[i];
    total.walkMi += useBerm ? a.walk_mi_berm[i] : a.walk_mi[i];
  }
  return { ...total, useBerm };
}
