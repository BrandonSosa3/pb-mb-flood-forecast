import { StatusPill } from "./StatusPill";
import {
  BERM_TOP_FT, type Forecast, type ForecastDay, dayLabel, headlineDay, summary, timeLabel, upcoming,
} from "../data";
import type { Spot } from "../search";

const NEVER_FT = 11; // above the highest level the pipeline tracks: "not in any expected flood"
const reaches = (v: number | null): v is number => v !== null && v <= NEVER_FT;
const ft = (v: number | null) => (reaches(v) ? `${v.toFixed(1)} ft` : "Above 11 ft");
const when = (d: ForecastDay, iso: string) => `${dayLabel(d.date)} around ${timeLabel(iso)}`;

/** Plain-language card for a searched spot: this week's bay water, the waves nearby, and the
 *  levels at which water reaches it. */
export function SpotCard({ spot, forecast, onShowLevel, onClose }: {
  spot: Spot; forecast: Forecast; onShowLevel: (level: number, bermHolds: boolean) => void; onClose: () => void;
}) {
  const area = forecast.areas.find((a) => a.name === spot.area);
  const days = area ? upcoming(area.days) : [];
  const peakDay = days.reduce<ForecastDay | undefined>((b, d) => (!b || d.bay_peak_ft > b.bay_peak_ft ? d : b), undefined);
  const head = headlineDay(days);
  const isStreet = spot.kind === "street";
  const here = isStreet ? "part of this street" : "here";

  // ---- bay side, this week ----
  let bayHead = "", bayNote = "", tone: "bad" | "watch" | "ok" = "ok";
  if (peakDay && spot.kind !== "landmark") {
    const peak = peakDay.bay_peak_ft, at = when(peakDay, peakDay.bay_peak_time);
    const now = peak >= BERM_TOP_FT ? spot.d : spot.db; // above the berm top the berm no longer matters
    if (reaches(now) && now <= peak) {
      bayHead = `Bay water likely reaches ${here}`; bayNote = `${at}.`; tone = "bad";
    } else if (reaches(spot.d) && spot.d <= peak) {
      bayHead = "Dry unless the bay-side berm fails";
      bayNote = `If the sand berm along Bayside Walk breaks, bay water reaches ${here} ${at}.`; tone = "watch";
    } else if (spot.g !== null && spot.g < peak) {
      bayHead = "No bay water on the surface this week";
      bayNote = `The ground here is lower than the high tide (${at}), so storm drains may back up.`; tone = "watch";
    } else {
      bayHead = "No bay water expected this week";
    }
  }

  // ---- ocean side: the closest call among nearby beach stretches ----
  let wave: { margin: number; day: ForecastDay; iso: string } | null = null;
  for (const d of days) {
    for (const p of spot.pts) {
      const s = d.stretches?.[p];
      if (s && (!wave || s[0] < wave.margin)) wave = { margin: s[0], day: d, iso: s[1] };
    }
  }
  let waveLine = "";
  if (wave) {
    if (wave.margin < 0) waveLine = `Waves may wash over the boardwalk nearby, ${when(wave.day, wave.iso)}.`;
    else if (wave.margin < 2) waveLine = `Waves may reach the top of the boardwalk nearby, ${when(wave.day, wave.iso)}. In past storms that meant water on the boardwalk.`;
    else waveLine = "Waves stay below the top of the boardwalk nearby this week.";
    if (wave.margin < 2 && tone === "ok") tone = "watch";
  }

  // The map slider runs 6–9.5 ft; offer a jump to the level where water first reaches this spot.
  const showAt = reaches(spot.db) && spot.db < BERM_TOP_FT ? { level: Math.max(spot.db, 6), holds: true }
    : reaches(spot.d) && spot.d <= 9.5 ? { level: Math.max(spot.d, 6), holds: false } : null;

  return (
    <aside className="detail spot" aria-label={`${spot.title} details`}>
      <div className="detail-head">
        <span className="stack-2">
          <strong>{spot.title}</strong>
          <span className="row-sub">{spot.area}</span>
        </span>
        <button type="button" className="icon-btn" aria-label="Close" onClick={onClose}>
          <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M6 6l12 12M18 6L6 18" /></svg>
        </button>
      </div>

      {spot.kind === "landmark" && head ? (
        <div className="stack-8">
          <div className="row-wrap"><StatusPill risk={head.risk} /><span className="row-sub">{dayLabel(head.date)}</span></div>
          <p className="body-14">{head.risk === "Low" ? "No flooding expected this week." : summary(head)}</p>
          {waveLine && <p className="body-14">{waveLine}</p>}
          <p className="fine">Tap a street or building nearby for its own numbers.</p>
        </div>
      ) : (
        <div className="stack-8">
          <div className={`spot-head tone-${tone}`}>
            <strong>{bayHead}</strong>
            {bayNote && <span>{bayNote}</span>}
          </div>
          {waveLine && <p className="body-14">{waveLine}</p>}
          <dl className="detail-list">
            <div><dt>Water reaches {here} at</dt><dd>{ft(spot.db)}{spot.db === BERM_TOP_FT && reaches(spot.d) && spot.d < BERM_TOP_FT ? " (berm top)" : ""}</dd></div>
            <div><dt>…if the berm fails</dt><dd>{ft(spot.d)}</dd></div>
            {isStreet && <div><dt>Road covered (berm fails)</dt><dd>{ft(spot.c ?? null)}</dd></div>}
            {peakDay && <div><dt>This week's highest bay level</dt><dd>{peakDay.bay_peak_ft.toFixed(1)} ft</dd></div>}
          </dl>
          {showAt && (
            <button type="button" className="chip chip-solid" onClick={() => onShowLevel(Math.round(showAt.level * 10) / 10, showAt.holds)}>
              Show the map at {showAt.level.toFixed(1)} ft
            </button>
          )}
          <span className="fine">Mission Bay level, feet above an ordinary low tide. "Reaches" means the ground next to
            it; floor heights are unknown.</span>
        </div>
      )}
    </aside>
  );
}
