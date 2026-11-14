import { useEffect, useRef, useState } from "react";

/** One month of the tide-gauge history: m = "YYYY-MM", a = feet above normal (null = gauge gap),
 *  n = El Niño winter name ("" if none), p = partial (current) month. */
export interface Month { m: string; a: number | null; n: string; p: boolean }

const NOW = "#0d3a73", NINO = "#4f8ad6", OTHER = "#a29e93";
const H = 190, PAD = { top: 22, right: 8, bottom: 22, left: 40 };
const Y_MIN = -0.5, Y_MAX = 1.25;
const LABELS: Record<string, string> = { "1982-83": "1982–83", "1997-98": "1997–98", "2015-16": "2015–16", "2026-27": "Now" };

const colorOf = (mo: Month) => (mo.n === "2026-27" ? NOW : mo.n ? NINO : OTHER);
const monthLabel = (ym: string) =>
  new Date(`${ym}-15T12:00:00`).toLocaleDateString("en-US", { month: "short", year: "numeric" });

/** Monthly extra water as thin columns: gray context, past El Niños and 2026 highlighted and labeled.
 *  Hover or tap reads out any month. */
export function ExtraWaterChart({ months }: { months: Month[] }) {
  const box = useRef<HTMLDivElement>(null);
  const [w, setW] = useState(340);
  const [hover, setHover] = useState<number | null>(null);

  useEffect(() => {
    const el = box.current;
    if (!el) return;
    const ro = new ResizeObserver(([e]) => setW(Math.max(260, Math.round(e.contentRect.width))));
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  const plotW = w - PAD.left - PAD.right, plotH = H - PAD.top - PAD.bottom;
  const step = plotW / months.length;
  const x = (i: number) => PAD.left + i * step;
  const y = (v: number) => PAD.top + ((Y_MAX - v) / (Y_MAX - Y_MIN)) * plotH;
  const barW = Math.max(1, step - (step > 3 ? 1 : 0));

  // Label each highlighted winter above its highest month.
  const peaks = new Map<string, number>();
  months.forEach((mo, i) => {
    if (!mo.n || mo.a === null) return;
    const j = peaks.get(mo.n);
    if (j === undefined || (months[j].a ?? -9) < mo.a) peaks.set(mo.n, i);
  });
  const years = months.map((mo, i) => ({ yr: Number(mo.m.slice(0, 4)), i })).filter((d, k, all) =>
    d.yr % 10 === 0 && all.findIndex((e) => e.yr === d.yr) === k);

  const onMove = (e: React.PointerEvent<SVGSVGElement>) => {
    const r = e.currentTarget.getBoundingClientRect();
    const i = Math.floor((e.clientX - r.left - PAD.left) / step);
    setHover(i >= 0 && i < months.length ? i : null);
  };
  const hm = hover !== null ? months[hover] : null;

  return (
    <div ref={box} className="xw-chart">
      <svg width={w} height={H} onPointerMove={onMove} onPointerDown={onMove} onPointerLeave={() => setHover(null)}
        role="img" aria-label="Bar chart of monthly extra water from 1980 to 2026. 2026 is far above every earlier month, including the 1982-83, 1997-98 and 2015-16 El Niños.">
        {[0, 0.5, 1].map((v) => (
          <g key={v}>
            <line x1={PAD.left} x2={w - PAD.right} y1={y(v)} y2={y(v)} className={v === 0 ? "xw-zero" : "xw-grid"} />
            <text x={PAD.left - 6} y={y(v) + 4} textAnchor="end" className="xw-tick">{v === 0 ? "0" : v === 1 ? "+1 ft" : `+${v}`}</text>
          </g>
        ))}
        {months.map((mo, i) => mo.a === null ? null : (
          <rect key={mo.m} x={x(i)} width={barW}
            y={mo.a >= 0 ? y(mo.a) : y(0)} height={Math.max(0.5, Math.abs(y(mo.a) - y(0)))}
            fill={colorOf(mo)} opacity={hover === null || hover === i ? 1 : 0.55} />
        ))}
        {[...peaks].map(([name, i]) => (
          <text key={name} x={Math.min(x(i) + barW / 2, w - PAD.right - 2)} y={y(months[i].a!) - 6}
            textAnchor={name === "2026-27" ? "end" : "middle"} className={name === "2026-27" ? "xw-label xw-label-now" : "xw-label"}>
            {LABELS[name] ?? name}
          </text>
        ))}
        {years.map(({ yr, i }) => (
          <text key={yr} x={x(i)} y={H - 6} textAnchor="start" className="xw-tick">{yr}</text>
        ))}
        {hm && <line x1={x(hover!) + barW / 2} x2={x(hover!) + barW / 2} y1={PAD.top} y2={H - PAD.bottom} className="xw-cross" />}
      </svg>
      {hm && (
        <div className="xw-tip" style={{ left: Math.min(Math.max(x(hover!) - 70, 0), w - 150) }}>
          <strong>{monthLabel(hm.m)}{hm.p ? " (so far)" : ""}</strong>
          <span>{hm.a === null ? "Gauge offline" : `${hm.a >= 0 ? "+" : "−"}${Math.abs(hm.a).toFixed(2)} ft vs normal`}</span>
          {hm.n && <span className="xw-tip-sub">{hm.n === "2026-27" ? "This El Niño" : `${LABELS[hm.n]} El Niño`}</span>}
        </div>
      )}
    </div>
  );
}
