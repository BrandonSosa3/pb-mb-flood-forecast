import { useEffect, useMemo, useRef, useState } from "react";
import maplibregl, { type ExpressionSpecification, type MapGeoJSONFeature } from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import { BERM_TOP_FT, type Curves, type Forecast, countsAt, loadCurves, upcoming } from "../data";
import { type Spot, loadSearch, spotFromKey } from "../search";
import { SpotCard } from "../components/SpotCard";

// Free, keyless, muted basemap (OpenStreetMap data, OpenFreeMap tiles).
const BASEMAP = "https://tiles.openfreemap.org/styles/positron";
const CENTER: [number, number] = [-117.2515, 32.7790]; // Mission Beach + south PB
const BLUE = "#2A78D6", DEEP = "#0D3A73", LIGHT = "#8FBCEF", AMBER = "#E3A008";
const OCT26 = 8.1;
const WATER = "#8EC1F0"; // lighter than the reached-building blue so the two read apart
// 3D camera: tilted, looking from the ocean toward the bay (east-northeast).
const VIEW_3D = { pitch: 55, bearing: 72 };
const PLAY_MS = 10000; // a whole event plays in about 10 seconds

interface PlayEvent {
  key: string; label: string; berm: "holds" | "fails"; note: string; peak_ft: number; peak_time: string; frames: [string, number][];
}

type Selected =
  | { kind: "street"; name: string; d: number; c: number; db: number; cb: number; g: number }
  | { kind: "building"; d: number; db: number; g: number };

export function MapScreen({ forecast, spotKey, start3d = false }: { forecast: Forecast; spotKey: string | null; start3d?: boolean }) {
  const container = useRef<HTMLDivElement>(null);
  const map = useRef<maplibregl.Map | null>(null);
  const [ready, setReady] = useState(false);
  const [noMap, setNoMap] = useState(false); // device can't draw the map (no WebGL)
  const [curves, setCurves] = useState<Curves | null>(null);
  const satPeak = useMemo(() => {
    const days = upcoming(forecast.areas[0]?.days ?? []);
    return days.length ? Math.max(...days.map((d) => d.bay_peak_ft)) : 6.5;
  }, [forecast]);
  const [level, setLevel] = useState(() => Math.round(satPeak * 10) / 10);
  // Start with the berm as it is this week (no berm in summer).
  const bermUpNow = forecast.areas[0]?.days.find((d) => d.berm_up !== undefined)?.berm_up ?? true;
  const [bermHolds, setBermHolds] = useState(bermUpNow);
  const [selected, setSelected] = useState<Selected | null>(null);

  const [view3d, setView3d] = useState(start3d);
  const [loading3d, setLoading3d] = useState(false);
  const [events, setEvents] = useState<PlayEvent[]>([]);
  const [playing, setPlaying] = useState<{ ev: PlayEvent; i: number } | null>(null);
  const [lastPlayed, setLastPlayed] = useState<PlayEvent | null>(null);
  const timer = useRef<number | null>(null);

  const [spot, setSpot] = useState<Spot | null>(null);
  const marker = useRef<maplibregl.Marker | null>(null);

  useEffect(() => { loadCurves().then(setCurves); }, []);
  useEffect(() => {
    fetch("/data/events.json").then((r) => (r.ok ? r.json() : null)).then((d) => d && setEvents(d.events)).catch(() => {});
    return () => { if (timer.current) window.clearInterval(timer.current); };
  }, []);

  // A place picked in search (#/map?spot=...): look it up, then fly there and drop a pin.
  useEffect(() => {
    if (!spotKey) { setSpot(null); return; }
    loadSearch().then((ix) => setSpot(spotFromKey(ix, spotKey))).catch(() => setSpot(null));
  }, [spotKey]);
  useEffect(() => {
    const m = map.current;
    marker.current?.remove();
    marker.current = null;
    if (!m || !ready || !spot) return;
    setSelected(null);
    // Keep the pin clear of the card: on phones it covers the top, on wide screens the right side.
    const wide = window.matchMedia("(min-width: 960px)").matches;
    const sheetPad = wide ? { top: 60, left: 60, right: 440, bottom: 60 } : { top: 280, left: 40, right: 40, bottom: 40 };
    if (spot.bbox) m.fitBounds([[spot.bbox[0], spot.bbox[1]], [spot.bbox[2], spot.bbox[3]]], { padding: sheetPad, maxZoom: 17.5, duration: 900 });
    else m.flyTo({ center: [spot.lon, spot.lat], zoom: spot.kind === "landmark" ? 16 : 17.5, offset: wide ? [-200, 0] : [0, 110], duration: 900 });
    marker.current = new maplibregl.Marker({ color: "#10202f" }).setLngLat([spot.lon, spot.lat]).addTo(m);
  }, [spot, ready]);
  const closeSpot = () => {
    setSpot(null);
    if (spotKey) history.replaceState(null, "", "#/map");
  };

  // Create the map once.
  useEffect(() => {
    if (!container.current || map.current) return;
    let m: maplibregl.Map;
    try {
      m = new maplibregl.Map({
        container: container.current, style: BASEMAP, center: CENTER, zoom: 14.9,
        minZoom: 12.5, maxZoom: 18.5, attributionControl: { compact: true },
        maxBounds: [[-117.32, 32.72], [-117.18, 32.84]],
      });
    } catch {
      setNoMap(true); // keep the controls and counts working without the map
      return;
    }
    m.addControl(new maplibregl.NavigationControl({ showCompass: false }), "top-right");
    m.on("load", () => {
      // Soft blue water so bay and ocean read as water at a glance (the basemap's default is gray).
      for (const layer of m.getStyle().layers) {
        if (layer.type === "fill" && /water/.test(layer.id)) m.setPaintProperty(layer.id, "fill-color", "#d4e4f1");
      }
      m.addSource("streets", { type: "geojson", data: "/data/streets.geojson" });
      m.addSource("buildings", { type: "geojson", data: "/data/buildings.geojson" });
      m.addLayer({ id: "buildings", type: "fill", source: "buildings", paint: { "fill-color": "#d9d7d0", "fill-opacity": 0 } });
      m.addLayer({
        id: "streets", type: "line", source: "streets",
        layout: { "line-cap": "round", "line-join": "round" },
        paint: { "line-width": ["interpolate", ["linear"], ["zoom"], 13, 2, 17, 7], "line-opacity": 0 },
      });
      for (const layer of ["streets", "buildings"]) {
        m.on("click", layer, (e) => e.features?.[0] && setSelected(toSelected(layer, e.features[0])));
        m.on("mouseenter", layer, () => (m.getCanvas().style.cursor = "pointer"));
        m.on("mouseleave", layer, () => (m.getCanvas().style.cursor = ""));
      }
      setReady(true);
    });
    map.current = m;
    return () => { m.remove(); map.current = null; };
  }, []);

  // Recolor buildings and streets whenever the level or berm switch changes.
  useEffect(() => {
    const m = map.current;
    if (!m || !ready) return;
    const useBerm = bermHolds && level < BERM_TOP_FT;
    const reach = (field: string): ExpressionSpecification => ["<=", ["coalesce", ["get", field], 99], level];
    const bDanger = useBerm ? "db" : "d";
    const below: ExpressionSpecification = ["<", ["coalesce", ["get", "g"], 99], level];
    m.setPaintProperty("buildings", "fill-color", ["case", reach(bDanger), BLUE, below, AMBER, "#d9d7d0"]);
    m.setPaintProperty("buildings", "fill-opacity", ["case", reach(bDanger), 0.85, below, 0.75, 0]);
    m.setPaintProperty("streets", "line-color", ["case", reach(useBerm ? "cb" : "c"), DEEP, LIGHT]);
    m.setPaintProperty("streets", "line-opacity", ["case", reach(useBerm ? "db" : "d"), 0.95, 0]);
  }, [level, bermHolds, ready]);

  // 3D: load the extra data the first time, then add tall buildings and the water surface.
  useEffect(() => {
    const m = map.current;
    if (!m || !ready) return;
    const phone = !window.matchMedia("(min-width: 960px)").matches;
    if (view3d) {
      if (!m.getSource("water3d")) {
        setLoading3d(true);
        m.addSource("water3d", { type: "geojson", data: "/data/water_bands.geojson" });
        m.addSource("bld3d", { type: "geojson", data: "/data/buildings3d.geojson" });
        m.addLayer({ id: "water-3d", type: "fill-extrusion", source: "water3d",
          paint: { "fill-extrusion-color": WATER, "fill-extrusion-height": 0.6, "fill-extrusion-opacity": 0.75 } });
        m.addLayer({ id: "bld-3d", type: "fill-extrusion", source: "bld3d",
          paint: { "fill-extrusion-height": ["coalesce", ["get", "h"], 6], "fill-extrusion-opacity": 0.92,
            "fill-extrusion-vertical-gradient": true } });
        m.on("click", "bld-3d", (e) => e.features?.[0] && setSelected(toSelected("buildings", e.features[0])));
        m.on("mouseenter", "bld-3d", () => (m.getCanvas().style.cursor = "pointer"));
        m.on("mouseleave", "bld-3d", () => (m.getCanvas().style.cursor = ""));
        const done = () => { if (m.isSourceLoaded("bld3d") && m.isSourceLoaded("water3d")) { setLoading3d(false); m.off("sourcedata", done); } };
        m.on("sourcedata", done);
      }
      for (const id of ["water-3d", "bld-3d"]) m.setLayoutProperty(id, "visibility", "visible");
      m.setLayoutProperty("buildings", "visibility", "none");
      m.easeTo({ ...VIEW_3D, pitch: phone ? 48 : VIEW_3D.pitch, zoom: Math.max(m.getZoom(), phone ? 14.8 : 15.3), duration: 1200 });
    } else if (m.getLayer("bld-3d")) {
      for (const id of ["water-3d", "bld-3d"]) m.setLayoutProperty(id, "visibility", "none");
      m.setLayoutProperty("buildings", "visibility", "visible");
      m.easeTo({ pitch: 0, bearing: 0, duration: 900 });
    }
  }, [view3d, ready]);

  // Raise the water and recolor the 3D buildings with the slider.
  useEffect(() => {
    const m = map.current;
    if (!m || !ready || !view3d || !m.getLayer("bld-3d")) return;
    const useBerm = bermHolds && level < BERM_TOP_FT;
    m.setFilter("water-3d", ["all", ["==", ["get", "berm"], useBerm ? 1 : 0], ["<=", ["get", "lv"], level + 1e-6]]);
    const reach: ExpressionSpecification = ["<=", ["coalesce", ["get", useBerm ? "db" : "d"], 99], level];
    const below: ExpressionSpecification = ["<", ["coalesce", ["get", "g"], 99], level];
    m.setPaintProperty("bld-3d", "fill-extrusion-color", ["case", reach, BLUE, below, AMBER, "#d9d7d0"]);
  }, [level, bermHolds, ready, view3d, loading3d]);

  const resetView = () => map.current?.easeTo({
    center: CENTER, zoom: view3d ? 15.3 : 14.9, ...(view3d ? VIEW_3D : { pitch: 0, bearing: 0 }), duration: 900,
  });

  const stop = () => {
    if (timer.current) window.clearInterval(timer.current);
    timer.current = null;
    setPlaying(null);
  };
  const play = (ev: PlayEvent) => {
    stop();
    setSelected(null);
    setBermHolds(ev.berm === "holds");
    setLastPlayed(ev);
    let i = 0;
    setPlaying({ ev, i });
    setLevel(ev.frames[0][1]);
    timer.current = window.setInterval(() => {
      i += 1;
      if (i >= ev.frames.length) { stop(); setLevel(Math.round(ev.peak_ft * 10) / 10); return; } // settle on the peak
      setPlaying({ ev, i });
      setLevel(ev.frames[i][1]);
    }, PLAY_MS / ev.frames.length);
  };
  const clock = (iso: string) => new Date(iso).toLocaleTimeString("en-US",
    { hour: "numeric", minute: "2-digit", timeZone: "America/Los_Angeles" }).replace(" AM", " am").replace(" PM", " pm");
  const frameTime = playing ? clock(playing.ev.frames[playing.i][0]) : "";

  const counts = curves ? countsAt(curves, level, bermHolds) : null;
  let headline = "", detail = "";
  if (counts) {
    if (counts.useBerm) {
      headline = "The berm holds back the bay";
      detail = counts.belowWater >= 25
        ? `${counts.belowWater.toLocaleString()} properties sit on ground lower than the water. Storm drains may back up into low streets.`
        : "Nothing beyond the shoreline.";
    } else if (counts.reached === 0) {
      headline = "Water stays at the shoreline";
      detail = "Beaches and some bayside paths get wet.";
    } else {
      headline = `Water reaches ${counts.reached.toLocaleString()} ${counts.reached === 1 ? "property" : "properties"}`;
      detail = `${counts.roadMi.toFixed(1)} miles of road covered` +
        (bermHolds && level >= BERM_TOP_FT ? `. The water is above the berm top (about ${BERM_TOP_FT} ft).` : ".");
    }
  }

  return (
    <main className="map-screen">
      <div ref={container} className="map" role="region" aria-label="Flood map of Pacific Beach and Mission Beach">
        {!noMap && (
          <div className="map-tools">
            <div className="segmented segmented-sm" role="group" aria-label="Map view">
              <button type="button" aria-pressed={!view3d} onClick={() => setView3d(false)}>2D</button>
              <button type="button" aria-pressed={view3d} onClick={() => setView3d(true)}>3D</button>
            </div>
            {view3d && <button type="button" className="chip chip-map" onClick={resetView}>Reset view</button>}
            {loading3d && <span className="chip chip-map" role="status">Loading 3D…</span>}
          </div>
        )}
        {noMap && (
          <div className="map-fallback">
            <strong>This device can't show the interactive map.</strong>
            <span>It needs WebGL, which is turned off or unsupported here. The water-level slider and counts still work,
              and the forecast pages show everything else.</span>
          </div>
        )}
      </div>
      {selected
        ? <DetailSheet sel={selected} level={level} bermHolds={bermHolds} onClose={() => setSelected(null)} />
        : spot && <SpotCard spot={spot} forecast={forecast} onClose={closeSpot}
            onShowLevel={(lv, holds) => { setLevel(lv); setBermHolds(holds); }} />}
      <section className="sheet" aria-label="Water level controls">
        <div className="sheet-top">
          <div className="stack-2">
            <span className="sheet-label">{playing ? `${playing.ev.label} · ${frameTime}` : "Mission Bay water level"}</span>
            <span className="sheet-level">{level.toFixed(1)} ft</span>
          </div>
          <span className="sheet-label">above low tide</span>
        </div>
        <label htmlFor="level" className="visually-hidden">Water level in feet</label>
        <input id="level" type="range" min={6} max={9.5} step={0.1} value={Math.max(6, Math.min(9.5, level))}
          onChange={(e) => { stop(); setLevel(Number(e.target.value)); }} className="slider" />
        <div className="chips">
          <button type="button" className="chip" onClick={() => { stop(); setLevel(Math.round(satPeak * 10) / 10); setBermHolds(bermUpNow); }}>
            Forecast peak · {satPeak.toFixed(1)} ft
          </button>
          <button type="button" className="chip" onClick={() => { stop(); setLevel(OCT26); setBermHolds(false); }}>
            Oct 26, 2026 · {OCT26} ft
          </button>
        </div>
        {events.length > 0 && (
          <div className="chips">
            {events.map((ev) => playing?.ev.key === ev.key
              ? <button key={ev.key} type="button" className="chip chip-solid" onClick={stop}>■ Stop</button>
              : <button key={ev.key} type="button" className="chip" onClick={() => play(ev)}>▶ Play {ev.label.replace(", 2026", "")}</button>)}
          </div>
        )}
        {lastPlayed && <p className="fine">{lastPlayed.label}: peak {lastPlayed.peak_ft.toFixed(1)} ft at
          {" "}{clock(lastPlayed.peak_time)}. {lastPlayed.note}</p>}
        <div className="segmented" role="group" aria-label="Bay-side sand berm">
          <button type="button" aria-pressed={bermHolds} onClick={() => { stop(); setBermHolds(true); }}>Berm holds</button>
          <button type="button" aria-pressed={!bermHolds} onClick={() => { stop(); setBermHolds(false); }}>Berm fails</button>
        </div>
        <div className="result" aria-live="polite">
          <span className="result-head">{headline}</span>
          <span className="result-detail">{detail}</span>
        </div>
        <div className="legend">
          <span><i style={{ background: BLUE }} /> Water reaches the property</span>
          <span><i style={{ background: AMBER }} /> Below water level (drains)</span>
          <span><i style={{ background: DEEP }} /> Road covered</span>
          {view3d && <span><i style={{ background: WATER }} /> Bay water surface</span>}
        </div>
      </section>
    </main>
  );
}

function toSelected(layer: string, f: MapGeoJSONFeature): Selected {
  const p = f.properties as Record<string, number | string>;
  const n = (k: string) => (typeof p[k] === "number" ? (p[k] as number) : 99);
  return layer === "streets"
    ? { kind: "street", name: String(p.name || "Unnamed path"), d: n("d"), c: n("c"), db: n("db"), cb: n("cb"), g: n("g") }
    : { kind: "building", d: n("d"), db: n("db"), g: n("g") };
}

function DetailSheet({ sel, level, bermHolds, onClose }: { sel: Selected; level: number; bermHolds: boolean; onClose: () => void }) {
  const ft = (x: number) => (x >= 90 ? "above 11 ft" : `${x.toFixed(1)} ft`);
  const useBerm = bermHolds && level < BERM_TOP_FT;
  const now = useBerm ? sel.db : sel.d;
  const state = now <= level ? "Water reaches it at this level" : sel.g < level ? "Below the water level: storm drains may back up" : "Dry at this level";
  return (
    <aside className="detail" aria-label="Details">
      <div className="detail-head">
        <strong>{sel.kind === "street" ? sel.name : "This property"}</strong>
        <button type="button" className="icon-btn" aria-label="Close details" onClick={onClose}>
          <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M6 6l12 12M18 6L6 18" /></svg>
        </button>
      </div>
      <span className="detail-state">{state}</span>
      <dl className="detail-list">
        <div><dt>Water reaches it (berm holds)</dt><dd>{ft(sel.db)}</dd></div>
        <div><dt>Water reaches it (berm fails)</dt><dd>{ft(sel.d)}</dd></div>
        {sel.kind === "street" && <div><dt>Road covered (berm fails)</dt><dd>{ft(sel.c)}</dd></div>}
        <div><dt>Lowest ground nearby</dt><dd>{ft(sel.g)}</dd></div>
      </dl>
      <span className="fine">Feet above an ordinary low tide. "Water reaches" means the ground next to it; floor heights are unknown.</span>
    </aside>
  );
}
