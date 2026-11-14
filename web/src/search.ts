// Street / address / landmark search. The whole list (search.json, built by
// pipeline/search_index.py) is downloaded once, so what people type never leaves the phone.

export interface StreetEntry {
  name: string; area: string; kind: "street" | "walkway";
  bbox: [number, number, number, number]; lon: number; lat: number;
  d: number | null; db: number | null; c: number | null; cb: number | null; g: number | null; pts: string[];
}
export interface LandmarkEntry { name: string; area: string; lon: number; lat: number; pt: string | null }
/** [house number, street index, lon, lat, d, db, g, area, pt] */
export type AddressRow = [string, number, number, number, number | null, number | null, number | null, string, string | null];
export interface SearchIndex { streets: StreetEntry[]; street_names: string[]; addresses: AddressRow[]; landmarks: LandmarkEntry[] }

/** A place picked in search, ready for the map. Heights in ft above an ordinary low tide.
 *  d/db = water reaches it (berm fails / holds); c/cb = road covered (streets only). */
export interface Spot {
  key: string; kind: "street" | "address" | "landmark"; title: string; area: string;
  lon: number; lat: number; bbox?: [number, number, number, number];
  d: number | null; db: number | null; c?: number | null; cb?: number | null; g: number | null;
  /** Nearby ocean-beach stretches (empty = not near the boardwalk). */
  pts: string[];
}

let cache: Promise<SearchIndex> | null = null;
export function loadSearch(): Promise<SearchIndex> {
  cache ??= fetch("/data/search.json").then((r) => {
    if (!r.ok) throw new Error(`search.json: ${r.status}`);
    return r.json();
  });
  cache.catch(() => (cache = null)); // let a later try reload after a network hiccup
  return cache;
}

const ABBR: Record<string, string> = {
  street: "st", avenue: "ave", av: "ave", boulevard: "blvd", bl: "blvd", place: "pl", court: "ct",
  drive: "dr", lane: "ln", road: "rd", terrace: "ter", north: "n", south: "s", east: "e", west: "w",
};
const words = (s: string) =>
  s.toLowerCase().replace(/[^a-z0-9 ]+/g, " ").split(/\s+/).filter(Boolean).map((w) => ABBR[w] ?? w);

/** Every query word must start some word of the name, in any order ("blvd mission" works). */
function matches(nameWords: string[], q: string[]) {
  return q.every((w) => nameWords.some((n) => n.startsWith(w)));
}

/** Short display form: "Mission Boulevard" -> "Mission Blvd". */
export function shortName(name: string) {
  return name.replace(/\bBoulevard\b/, "Blvd").replace(/\bStreet\b/, "St").replace(/\bAvenue\b/, "Ave")
    .replace(/\bPlace\b/, "Pl").replace(/\bCourt\b/, "Ct").replace(/\bDrive\b/, "Dr");
}

export function spotFromKey(ix: SearchIndex, key: string): Spot | null {
  const [t, n] = [key[0], Number(key.slice(1))];
  if (t === "s" && ix.streets[n]) {
    const s = ix.streets[n];
    return { key, kind: "street", title: shortName(s.name), area: s.area, lon: s.lon, lat: s.lat, bbox: s.bbox,
      d: s.d, db: s.db, c: s.c, cb: s.cb, g: s.g, pts: s.pts };
  }
  if (t === "a" && ix.addresses[n]) {
    const [num, si, lon, lat, d, db, g, area, pt] = ix.addresses[n];
    return { key, kind: "address", title: `${num} ${shortName(ix.street_names[si])}`, area, lon, lat, d, db, g, pts: pt ? [pt] : [] };
  }
  if (t === "l" && ix.landmarks[n]) {
    const l = ix.landmarks[n];
    return { key, kind: "landmark", title: l.name, area: l.area, lon: l.lon, lat: l.lat, d: null, db: null, g: null, pts: l.pt ? [l.pt] : [] };
  }
  return null;
}

export interface Hit { key: string; title: string; sub: string }

export function search(ix: SearchIndex, query: string, limit = 6): Hit[] {
  const q = words(query);
  if (!q.length) return [];
  const hits: (Hit & { rank: number })[] = [];
  const num = /^\d+[a-z]?$/.test(q[0]) ? q[0] : null;

  if (num) {
    const rest = q.slice(1);
    const streetOk = ix.street_names.map((n) => rest.length === 0 || matches(words(n), rest));
    ix.addresses.forEach(([n, si, , , , , , area], i) => {
      if (!streetOk[si] || !n.toLowerCase().startsWith(num)) return;
      hits.push({ key: `a${i}`, title: `${n} ${shortName(ix.street_names[si])}`, sub: area,
        rank: (n.toLowerCase() === num ? 0 : 1) * 10 + (rest.length ? 0 : 5) });
    });
    // Not every house number is in OpenStreetMap: offer the nearest listed number on that street.
    if (!hits.length && rest.length) {
      const want = parseInt(num, 10);
      const best = new Map<number, { i: number; gap: number }>();
      ix.addresses.forEach(([n, si], i) => {
        if (!streetOk[si]) return;
        const gap = Math.abs(parseInt(n, 10) - want);
        if (!best.has(si) || gap < best.get(si)!.gap) best.set(si, { i, gap });
      });
      for (const { i, gap } of best.values()) {
        if (gap > 200) continue;
        const [n, si, , , , , , area] = ix.addresses[i];
        hits.push({ key: `a${i}`, title: `${n} ${shortName(ix.street_names[si])}`, sub: `Nearest listed address · ${area}`, rank: 1 });
      }
    }
  }
  ix.landmarks.forEach((l, i) => {
    if (matches(words(l.name), q)) hits.push({ key: `l${i}`, title: l.name, sub: l.area, rank: 2 });
  });
  const landmarkNames = new Set(ix.landmarks.map((l) => l.name));
  ix.streets.forEach((s, i) => {
    const w = words(s.name);
    if (!matches(w, q) || landmarkNames.has(s.name)) return;
    hits.push({ key: `s${i}`, title: shortName(s.name), sub: `${s.kind === "walkway" ? "Path" : "Street"} · ${s.area}`,
      rank: w[0].startsWith(q[0]) ? 3 : 4 });
  });
  return hits.sort((a, b) => a.rank - b.rank || a.title.localeCompare(b.title, "en", { numeric: true }))
    .slice(0, limit).map(({ rank: _, ...h }) => h);
}
