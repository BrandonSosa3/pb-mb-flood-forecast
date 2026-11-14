import { useState } from "react";
import { StatusPill } from "../components/StatusPill";
import {
  BERM_TOP_FT, type Forecast, type ForecastDay, dayLabel, headlineDay, riskIndex, slug, summary, timeLabel, upcoming,
} from "../data";

function longDate(date: string) {
  return new Date(`${date}T12:00:00`).toLocaleDateString("en-US", { weekday: "short", month: "short", day: "numeric" });
}

const surfText = ([a, b]: [number, number]) => (a === b ? `${a}` : `${a}–${b}`);

export function Area({ forecast, areaSlug }: { forecast: Forecast; areaSlug: string }) {
  const area = forecast.areas.find((a) => slug(a.name) === areaSlug);
  const days = area ? upcoming(area.days).slice(0, 4) : [];
  const [picked, setPicked] = useState<string | null>(null);
  if (!area || days.length === 0) {
    return <main className="screen"><a href="#/" className="back">‹ All areas</a><h1>Area not found</h1></main>;
  }
  const day = days.find((d) => d.date === picked) ?? headlineDay(days)!;
  const hasBeach = day.wave_height_ft !== null;
  const tide = forecast.extra_water_ft !== null ? day.bay_peak_ft - forecast.extra_water_ft : null;

  return (
    <main className="screen">
      <a href="#/" className="back">
        <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M15 5l-7 7 7 7" /></svg>
        All areas
      </a>

      <div className="area-cols">
      <div className="col">
      <div className="stack-8">
        <h1 className="h1-lg">{area.name}</h1>
        <div className="row-wrap">
          <StatusPill risk={day.risk} size="lg" />
          <span className="muted-15">
            {longDate(day.date)}
            {day.risk !== "Low" && <> · around {timeLabel(day.worst_time ?? day.bay_peak_time)}</>}
          </span>
        </div>
        <p className="lead">{summary(day)}</p>
        {riskIndex(day.could_reach) > riskIndex(day.risk) && (
          <p className="note">Could reach <strong>{day.could_reach}</strong>: the two wave models disagree
            (waves reach the boardwalk top at {day.stretches_reach_top ?? 0} vs {day.stretches_reach_top_upper} spots).</p>
        )}
      </div>

      <section className="panel">
        <div className="section-label">Next {days.length} days</div>
        <div className="days days-tight" role="group" aria-label="Pick a day">
          {days.map((d) => (
            <button key={d.date} type="button" className={`day-btn tint-${d.risk.toLowerCase()}`}
              aria-pressed={d.date === day.date} onClick={() => setPicked(d.date)}>
              <span className="day-name">{dayLabel(d.date)}</span>
              <span className="day-risk-dark">{d.risk}</span>
              <span className="day-cause">{causeWord(d)}</span>
            </button>
          ))}
        </div>
      </section>

      <BermCard day={day} />
      </div>

      <div className="col">
      <section className="stack-10">
        <h2 className="h2-top">What's driving it</h2>
        <div className="tiles">
          <Tile label="Tide" value={tide !== null ? `${tide.toFixed(1)} ft` : "—"} note={`High tide ${timeLabel(day.bay_peak_time)}`} />
          <Tile label="Extra water" value={forecast.extra_water_ft !== null ? `+${forecast.extra_water_ft.toFixed(1)} ft` : "—"}
            note="El Niño is holding the ocean higher than normal" />
          {hasBeach
            ? <Tile label="Surf" value={day.surf_ft ? `Sets ~${surfText(day.surf_ft)} ft` : `${Math.round(day.wave_height_ft![0])}–${Math.round(day.wave_height_ft![1])} ft`}
                note={`Waves ${day.wave_period_s![0]}–${day.wave_period_s![1]} seconds apart`} />
            : <Tile label="Waves" value="—" note="Bay shore: no ocean waves" />}
        </div>
        {hasBeach && day.nws_surf && <p className="body-14">National Weather Service surf forecast: {day.nws_surf}.</p>}
        <p className="fine">Tide and extra water are feet above an ordinary low tide. Surf is our estimate of the bigger
          waves as they break. For flood risk we use the higher of two wave forecasts, because the lower one has
          come in too small.</p>
      </section>

      {day.places_to_watch.length > 0 && (
        <section className="stack-10">
          <h2>Places to watch</h2>
          <div className="list">
            {day.places_to_watch.map((p) => (
              <a key={p.point} href="#/map" className="list-row">
                <span className="stack-2">
                  <span className="row-title">Boardwalk at {p.near}</span>
                  <span className="row-sub">{p.over
                    ? `Waves may wash ${Math.abs(p.margin_ft).toFixed(1)} ft over the top`
                    : `Waves may reach within ${p.margin_ft.toFixed(1)} ft of the top`}</span>
                </span>
                <svg viewBox="0 0 24 24" aria-hidden="true" className="chev"><path d="M9 5l7 7-7 7" /></svg>
              </a>
            ))}
          </div>
        </section>
      )}

      <a href="#/map" className="button-primary">
        <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M9 4L3 6v14l6-2 6 2 6-2V4l-6 2-6-2z" /><path d="M9 4v14M15 6v14" /></svg>
        See it on the map
      </a>
      <a href="#/about" className="link-center">How this forecast is made</a>
      </div>
      </div>
    </main>
  );
}

function causeWord(d: ForecastDay) {
  if (d.risk === "Low") return "—";
  if (d.cause === "ocean") return "waves";
  if (d.cause === "both") return "waves + bay";
  return d.properties_reached > 0 ? "bay" : "drains";
}

function Tile({ label, value, note }: { label: string; value: string; note: string }) {
  return (
    <div className="tile">
      <span className="tile-label">{label}</span>
      <span className="tile-value">{value}</span>
      <span className="tile-note">{note}</span>
    </div>
  );
}

function BermCard({ day }: { day: ForecastDay }) {
  const fails = day.risk_if_berm_fails;
  return (
    <section className="panel stack-8 berm-card">
      <h2 className="h2-sm">Bay side: the sand berm</h2>
      {day.berm_overtopped ? (
        <p className="body-15">Mission Bay is forecast to reach {day.bay_peak_ft.toFixed(1)} ft, above the top of the
          City's sand berm along Bayside Walk (about {BERM_TOP_FT.toFixed(0)} ft). Expect bay water in low streets.</p>
      ) : (
        <p className="body-15">The City's sand berm along Bayside Walk holds back Mission Bay. The bay peak is about{" "}
          {day.bay_peak_ft.toFixed(1)} ft, below the berm top (about {BERM_TOP_FT.toFixed(0)} ft).
          {day.properties_below_water >= 25 &&
            <> About {roundTo10(day.properties_below_water).toLocaleString()} properties sit on ground lower than that,
            so storm drains may back up into low streets.</>}
        </p>
      )}
      {!day.berm_overtopped && (
        <div className="kv">
          <span>If the berm fails at this tide</span>
          <strong>{fails === day.risk ? `Still ${fails}` : fails}
            {day.properties_if_berm_fails > 0 && ` · ${roundTo10(day.properties_if_berm_fails).toLocaleString()} properties`}</strong>
        </div>
      )}
      <p className="fine">On Oct 26, 2026 the berm broke with Mission Bay at about 8.1 ft and water reached about
        1,100 properties in Mission Beach.</p>
    </section>
  );
}

function roundTo10(n: number) {
  return n < 20 ? n : Math.round(n / 10) * 10;
}
