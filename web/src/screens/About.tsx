import { useEffect, useState } from "react";
import { NWS_URL } from "../data";
import { ExtraWaterChart, type Month } from "../components/ExtraWaterChart";

// "How it works": the method in plain words, the honest track record, and the limits.
// Technical terms live only inside the tap-to-open sections, each explained.

type Result = "right" | "close" | "missed" | "false_alarm" | "pending";
interface TrackDay {
  date: string; label: string; side: "bay" | "waves"; how: "backtest" | "live";
  title: string; happened: string; we_said: string; result: Result; note?: string;
  sources: { name: string; url?: string }[];
}
interface About {
  history: { station_name: string; downloaded: string; months: Month[]; record_before_2026: { month: string; anomaly_ft: number } };
  track_record: { updated: string; days: TrackDay[] };
  log: { first: string | null; count: number };
}

const RESULT: Record<Result, { word: string; cls: string }> = {
  right: { word: "Right", cls: "res-right" },
  close: { word: "Close", cls: "res-close" },
  missed: { word: "Missed", cls: "res-wrong" },
  false_alarm: { word: "False alarm", cls: "res-wrong" },
  pending: { word: "Waiting", cls: "res-pending" },
};

const monthName = (ym: string) =>
  new Date(`${ym}-15T12:00:00`).toLocaleDateString("en-US", { month: "short", year: "numeric" });

export function About() {
  const [about, setAbout] = useState<About | null>(null);
  const [error, setError] = useState(false);
  useEffect(() => {
    fetch("/data/about.json", { cache: "no-cache" })
      .then((r) => (r.ok ? r.json() : Promise.reject()))
      .then(setAbout)
      .catch(() => setError(true));
  }, []);

  const days = about?.track_record.days ?? [];
  const n = (r: Result) => days.filter((d) => d.result === r).length;
  const wrong = n("missed") + n("false_alarm");
  const months = about?.history.months ?? [];
  const latest = [...months].reverse().find((m) => m.a !== null && !m.p);
  const record = about?.history.record_before_2026;

  return (
    <main className="screen about">
      <div className="stack-8">
        <div className="eyebrow">PB &amp; MB Flood Forecast</div>
        <h1>How this forecast works</h1>
        <p className="lead">A free, independent forecast of where ocean and bay water may reach in Pacific Beach and
          Mission Beach, street by street, for the next few days.</p>
        <div className="notice">This is not an official warning. For official alerts,{" "}
          <a href={NWS_URL}>check the National Weather Service</a>.</div>
      </div>

      {/* 1 · The idea */}
      <section className="stack-10">
        <div className="step-label">1 · The idea</div>
        <h2 className="h2-flush">Three things stack up</h2>
        <IdeaDrawing />
        <p className="body-15">How high the water gets = the <strong>tide</strong> + <strong>extra water</strong> the ocean
          is carrying this winter + how far <strong>waves</strong> rush up the beach. If that is higher than the ground, and
          the water has a path to get there, it floods.</p>
        <p className="fine">The path matters: a low spot behind higher ground stays dry unless water can flow to it. On the
          bay side there are no big waves, so it's just tide + extra water.</p>
      </section>

      {/* 2 · This winter */}
      <section className="stack-10">
        <div className="step-label">2 · This winter is different</div>
        <h2 className="h2-flush">The ocean is sitting about 1 ft higher than normal</h2>
        {about ? (
          <div className="panel stack-8">
            <div className="chart-title">Extra water each month, 1980 to now</div>
            <ExtraWaterChart months={months} />
            <div className="chart-legend" aria-hidden="true">
              <span><i className="sw sw-now" /> 2026</span>
              <span><i className="sw sw-nino" /> Past strong El Niños</span>
              <span><i className="sw sw-other" /> Other months</span>
            </div>
            <p className="fine">Feet above normal for that month (after removing slow sea-level rise), NOAA{" "}
              {about.history.station_name} tide gauge. Tap or hover for a month.</p>
          </div>
        ) : (
          <div className="skeleton" style={{ height: 230 }} />
        )}
        {latest && record && (
          <p className="body-15">In {monthName(latest.m)} the water sat <strong>{latest.a!.toFixed(1)} ft</strong> above
            normal. The highest month in the 45 years before 2026 was {monthName(record.month)}, during the 1982–83
            El Niño, at {record.anomaly_ft.toFixed(1)} ft. A slow ocean wave from the tropics (a Kelvin wave) plus El Niño
            are holding the water up. That foot is added to every high tide this winter.</p>
        )}
      </section>

      {/* 3 · Pieces */}
      <section className="stack-10">
        <div className="step-label">3 · Where each piece comes from</div>
        <div className="list">
          <Piece title="Tide" source="NOAA tide predictions">
            NOAA predicts the ordinary tide years ahead from the Moon and Sun. We use its predictions for La Jolla (ocean)
            and Mission Bay. The highest tides of the year, "king tides", come around late December.
          </Piece>
          <Piece title="Extra water" source="NOAA tide gauges, measured">
            The La Jolla gauge measures the real water level every 6 minutes. Measured minus predicted = extra water. We
            average it over the last day and assume it stays about the same for the next few days (it changes slowly).
          </Piece>
          <Piece title="Waves" source="Scripps CDIP wave forecasts">
            Scripps Institution of Oceanography's CDIP forecasts wave height, period (seconds between waves) and direction
            every ~100 m along the coast. We use two versions, driven by NOAA's and by Europe's (ECMWF) weather models. We
            check both against what really happened after every forecast; the NOAA-driven one has come in too small, so
            for flood risk we use whichever is higher, stretch by stretch and hour by hour.
          </Piece>
          <Piece title="Ground height" source="USGS laser survey, Nov 2024">
            A plane scanned the ground with lasers (lidar), giving its height every 1 m (about 3 ft). That shows the height
            of every street, the boardwalk, the seawall and the bay-side sand berm.
          </Piece>
        </div>
      </section>

      {/* 4 · Track record */}
      <section className="stack-10">
        <div className="step-label">4 · Track record</div>
        <h2 className="h2-flush">Tested against real floods</h2>
        {about ? (
          <>
            <div className="score">
              <Score n={n("right")} word="right" cls="res-right" />
              <Score n={n("close")} word="close" cls="res-close" />
              <Score n={wrong} word="wrong" cls="res-wrong" />
              {n("pending") > 0 && <Score n={n("pending")} word="waiting" cls="res-pending" />}
            </div>
            <p className="fine">"Right" means the risk we gave matches what news reports and photos show. Most of these are
              tests run afterwards, feeding the model the tide and waves that were really measured that day.</p>
            <div className="list">
              {days.map((d) => <TrackRow key={d.date + d.title} d={d} />)}
            </div>
            <div className="panel stack-8">
              <strong className="body-15">Every forecast is saved before the event</strong>
              <p className="fine">Since Nov 13, 2026 a computer saves each new forecast twice a day, before anything happens,
                so it can be checked honestly afterwards, including the December king tides.
                {about.log.count > 0 && <> {about.log.count} forecasts saved so far.</>}</p>
            </div>
          </>
        ) : error ? (
          <p className="fine">Track record unavailable right now.</p>
        ) : (
          <div className="skeleton" style={{ height: 260 }} />
        )}
      </section>

      {/* 5 · Limits */}
      <section className="stack-10">
        <div className="step-label">5 · What it can't do</div>
        <ul className="limits">
          <li><strong>It doesn't know floor heights.</strong> "Water reaches this property" means the ground next to it, not
            that water gets inside.</li>
          <li><strong>It can't predict a sand berm breaking.</strong> That's why the app shows "if the berm fails" as a
            second rating.</li>
          <li><strong>It doesn't model storm drains.</strong> It flags streets lower than the water, where drains may back
            up, but can't say whether they will.</li>
          <li><strong>Bay water spreads instantly in the model.</strong> For a short high tide, real water may not get as
            far.</li>
          <li><strong>On the ocean side it tends to understate.</strong> When waves come within about 2 ft of the boardwalk
            top, in past events there was already water on the boardwalk.</li>
          <li><strong>Beaches change shape.</strong> The ground map is from Nov 2024; winter storms can lower the sand.</li>
          <li><strong>Only a handful of events so far.</strong> The track record grows with every high tide and swell.</li>
        </ul>
      </section>

      <Technical updated={about?.history.downloaded} />

      <p className="fine center">Made by Brandon Sosa · Data: NOAA, Scripps CDIP, USGS, OpenStreetMap contributors</p>
    </main>
  );
}

function Score({ n, word, cls }: { n: number; word: string; cls: string }) {
  return (
    <div className="score-cell">
      <span className={`score-n ${cls}`}>{n}</span>
      <span className="score-word">{word}</span>
    </div>
  );
}

function Piece({ title, source, children }: { title: string; source: string; children: React.ReactNode }) {
  return (
    <details className="disclosure">
      <summary>
        <span className="stack-2"><span className="row-title">{title}</span><span className="row-sub">{source}</span></span>
        <Chevron />
      </summary>
      <p className="body-14">{children}</p>
    </details>
  );
}

function TrackRow({ d }: { d: TrackDay }) {
  const r = RESULT[d.result];
  return (
    <details className="disclosure">
      <summary>
        <span className="stack-2">
          <span className="row-sub">{d.label} · {d.side === "bay" ? "Bay side" : "Ocean waves"}</span>
          <span className="row-title">{d.title}</span>
        </span>
        <span className="row-end">
          <span className={`res ${r.cls}`}><ResultIcon result={d.result} />{r.word}</span>
          <Chevron />
        </span>
      </summary>
      <div className="stack-8 track-body">
        <div><div className="kv-label">What happened</div><p className="body-14">{d.happened}</p></div>
        <div><div className="kv-label">What the model said</div><p className="body-14">{d.we_said}</p></div>
        {d.note && <p className="fine">{d.note}</p>}
        <p className="fine">{d.how === "live" ? "Forecast saved before the event." : "Tested afterwards with the real measured tide and waves."}
          {d.sources.length > 0 && <> Sources: {d.sources.map((s, i) => (
            <span key={s.name}>{i > 0 && ", "}{s.url ? <a href={s.url} target="_blank" rel="noreferrer">{s.name}</a> : s.name}</span>
          ))}.</>}
        </p>
      </div>
    </details>
  );
}

function ResultIcon({ result }: { result: Result }) {
  const path = result === "right" ? "M5 12l5 5 9-10"
    : result === "close" ? "M6 12h12"
    : result === "pending" ? "M12 7v5l3 2"
    : "M7 7l10 10M17 7L7 17";
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true" className="res-icon">
      {result === "pending" && <circle cx="12" cy="12" r="8" />}
      <path d={path} />
    </svg>
  );
}

function Chevron() {
  return <svg viewBox="0 0 24 24" aria-hidden="true" className="chev disclosure-chev"><path d="M9 5l7 7-7 7" /></svg>;
}

/** Simple beach cross-section: tide, extra water and wave run-up stacked against the ground. */
function IdeaDrawing() {
  return (
    <svg viewBox="0 0 340 170" className="idea" role="img"
      aria-label="Drawing: the tide, plus extra water, plus waves rushing up the beach, compared with the height of the boardwalk">
      {/* water layers (ocean on the left) */}
      <rect x="0" y="118" width="200" height="52" fill="#cfe0f5" />
      <rect x="0" y="100" width="222" height="18" fill="#8fbcef" />
      {/* wave run-up wedge up the beach slope */}
      <path d="M150 100 Q 190 92 252 70 L 262 70 L 262 100 Z" fill="#2a78d6" opacity="0.85" />
      {/* ground: beach slope up to the boardwalk, then the street behind */}
      <path d="M0 170 L 0 160 L 120 150 L 270 64 L 300 64 L 300 66 L 340 66 L 340 170 Z" fill="#e8dcc3" />
      <rect x="270" y="58" width="30" height="6" fill="#a3896a" rx="1.5" />
      <path d="M0 160 L 120 150 L 270 64 L 300 64 L 300 66 L 340 66" fill="none" stroke="#8a7458" strokeWidth="1.5" />
      {/* labels */}
      <g className="idea-label">
        <text x="10" y="148">Tide</text>
        <text x="10" y="113">+ Extra water</text>
        <text x="152" y="62">+ Waves rush up</text>
        <text x="262" y="50">Boardwalk</text>
      </g>
    </svg>
  );
}

function Technical({ updated }: { updated?: string }) {
  return (
    <details className="disclosure panel-disclosure">
      <summary>
        <span className="row-title">For the technically curious</span>
        <Chevron />
      </summary>
      <div className="stack-10 track-body">
        <Term t="Heights (MLLW)">All heights are feet above <em>mean lower low water</em> (MLLW): the average of each
          day's lower low tide at La Jolla, NOAA's usual zero for tides. The lidar is in NAVD88, a land survey zero; at La
          Jolla NAVD88 is 0.19 ft above MLLW.</Term>
        <Term t="Extra water">Measured − predicted water level (NOAA calls it the residual, or non-tidal water level),
          averaged over 25 hours to smooth out wiggles. The chart above shows monthly averages minus a straight-line
          sea-level-rise trend fitted on non-El Niño years (+0.09 ft per decade at San Diego).</Term>
        <Term t="Wave run-up (R2)">Stockdon et al. (2006): an empirical formula from wave height, wave period and beach
          slope that gives the height only the top 2% of waves reach. Wave heights come from CDIP MOP points at 10 m depth,
          converted back to deep water. Beach slope and boardwalk/ridge top are measured from the lidar at each of 53 points
          about 100 m apart. "Reaches" = within 2 ft of the top; "over" = above it. In practice "reaches" has meant water
          on the boardwalk (Dec 2023, Nov 14 2026).</Term>
        <Term t="Surf size">The breaking height of the bigger waves, from Komar &amp; Gaylord (1972): 0.39 g<sup>1/5</sup>(T H<sub>0</sub><sup>2</sup>)<sup>2/5</sup>,
          using the average of the two wave models. A size readout only (flood risk uses run-up). Shown next to the NWS Surf
          Zone Forecast, which is the official number; ours tends to match NWS's set size.</Term>
        <Term t="Checking the wave forecasts">After every forecast, each saved wave forecast is compared with CDIP's
          nowcast (the same model driven by measured buoys). First result (Nov 13–14, 2026): NOAA-driven about 85% of the
          actual height, ECMWF-driven about 105%. Updated twice a day in the project's wave check.</Term>
        <Term t="Where bay water can go">For every 1 m cell, the lowest water level at which water from the bay can flow
          there without going over higher ground (a "connected" flood fill, using morphological reconstruction). Each
          building gets the lowest value within 2 m of it; streets are split into 25 m pieces.</Term>
        <Term t="The berm">The City piles a temporary sand berm along Bayside Walk in winter. Its height isn't published;
          we assume a top of 9.0 ft. The headline assumes it holds; the second rating removes it.</Term>
        <Term t="Risk levels">Each area takes the worse of its bay and ocean sides. Bay: Minor from 3 properties reached, 0.1 mile of bayside path
          or 25 below the water (storm drains); Moderate from 25 reached or ¼ mile of road; Major from 200 reached or 1 mile.
          Ocean: Minor if waves reach the top at 1 spot; Moderate at 5, or water over at 1; Major if over at 3.</Term>
        <Term t="Rain">Storm drains in these neighborhoods empty into Mission Bay and the ocean; near high tide their outlets
          are underwater, so rain can't drain and ponds in low streets. Rule: at least 0.25 in of rain (NWS hourly forecast)
          within 3 hours of the day's highest tide, where 10+ properties sit on ground below the water, raises the rating
          one level (at most to Moderate). Since 2000 that happened about once a year at the San Diego airport gauge,
          including the record storm of Jan 22, 2024. Rain flooding away from the coast (hillsides, canyons) isn't
          modeled yet.</Term>
        <Term t="3D view">Building heights come from the same 2024 USGS lidar survey: the height of laser hits on each
          roof minus the ground under it. The blue water surface is the bay flood model cut into 0.1 ft steps. "Play"
          replays a real high tide every 20 minutes (Mission Bay prediction + extra water measured at La Jolla). The exact
          time the berm broke on Oct 26 wasn't reported, so that replay shows the berm gone for the whole tide. Building
          height is for the picture only; floor heights are unknown.</Term>
        <Term t="Not the same as sea-level-rise maps">USGS CoSMoS and NOAA's viewer show long-term sea level rise
          (decades). This forecasts the next few days, with this winter's real tide, extra water and waves.</Term>
        <Term t="Data">NOAA CO-OPS (tide gauges 9410230 La Jolla, 9410170 San Diego, 9410196 Mission Bay predictions);
          Scripps CDIP MOP forecasts (WaveWatch III and ECMWF), hindcast and nowcast; USGS 3DEP 1 m lidar
          CA_SanDiegoCo_D24 (flown Nov 2024); OpenStreetMap buildings and streets (addresses removed); NWS alerts, Surf Zone
          Forecast and hourly weather forecast.
          {updated && <> Tide history downloaded {updated}.</>} Forecast inputs refresh twice a day.</Term>
      </div>
    </details>
  );
}

function Term({ t, children }: { t: string; children: React.ReactNode }) {
  return <div><div className="kv-label">{t}</div><p className="body-14">{children}</p></div>;
}
