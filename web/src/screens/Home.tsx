import { SearchBox } from "../components/SearchBox";
import { StatusDot, StatusPill } from "../components/StatusPill";
import {
  type Forecast, type Risk, NWS_URL, dayLabel, headlineDay, rainHeadline, rainSummary, rainUpcoming, rainWindow, riskIndex,
  slug, summary, timeLabel, upcoming, updatedLabel, worse,
} from "../data";

export function Home({ forecast }: { forecast: Forecast }) {
  const areas = forecast.areas.map((a) => ({ ...a, days: upcoming(a.days) }));
  const dates = areas[0]?.days.slice(0, 4).map((d) => d.date) ?? [];
  const worstOn = (date: string): Risk =>
    areas.reduce<Risk>((w, a) => worse(w, a.days.find((d) => d.date === date)?.risk ?? "Low"), "Low");
  const alerts = forecast.nws_alerts.filter((a) => /coastal flood|high surf/i.test(a.event));

  return (
    <main className="screen">
      <div className="home-head">
        <div>
          <div className="eyebrow">PB &amp; MB Flood Forecast</div>
          <h1>Is my area at risk this week?</h1>
          <div className="sub">Updated {updatedLabel(forecast.issued_at)}</div>
        </div>
        <SearchBox />
      </div>

      <div className="area-grid">
      {areas.map((area) => {
        const day = headlineDay(area.days);
        if (!day) return null;
        const extra: string[] = [];
        if (day.risk !== "Low") extra.push(`Worst: ${dayLabel(day.date)} around ${timeLabel(day.worst_time ?? day.bay_peak_time)}`);
        const wet = upcoming(area.days).find((d) => d.rain_ponding);
        if (wet && wet !== day) extra.push(`Rain ${dayLabel(wet.date)} during high tide: low streets may pond`);
        if (riskIndex(day.could_reach) > riskIndex(day.risk)) extra.push(`Could reach ${day.could_reach}`);
        else if (riskIndex(day.risk_if_berm_fails) > riskIndex(day.risk)) extra.push(`${day.risk_if_berm_fails} if the bay berm fails`);
        return (
          <a key={area.name} className="card" href={`#/area/${slug(area.name)}`}>
            <div className="card-head">
              <span className="card-title">{area.name}</span>
              <StatusPill risk={day.risk} />
            </div>
            <div className="card-body">{day.risk === "Low" ? "No flooding expected this week." : summary(day)}</div>
            {extra.length > 0 && <div className="card-foot">{extra.map((t) => <span key={t}>{t}</span>)}</div>}
          </a>
        );
      })}
      </div>

      <RainSection forecast={forecast} />

      <div className="home-foot">
      <div className="stack-8">
      <div className="section-label">Next {dates.length} days, all areas</div>
      <div className="days">
        {dates.map((date) => {
          const r = worstOn(date);
          return (
            <div className="day" key={date}>
              <span className="day-name">{dayLabel(date)}</span>
              <StatusDot risk={r} />
              <span className="day-risk">{r}</span>
            </div>
          );
        })}
      </div>

      </div>

      <div className="notice">
        {alerts.length > 0 && (
          <>Official: {alerts.map((a) => `NWS ${a.event}`).join(" and ")} in effect. </>
        )}
        This app is not an official warning. <a href={NWS_URL}>Check the National Weather Service</a>.
      </div>
      </div>
    </main>
  );
}

function RainSection({ forecast }: { forecast: Forecast }) {
  const rain = forecast.rain;
  if (!rain || rain.areas.length === 0) return null;
  const heads = rain.areas.map((a) => ({ area: a, day: rainHeadline(a.days) }));
  const risky = heads.filter((h) => h.day && h.day.level !== "Low");
  const days = rainUpcoming(rain.areas[0].days);
  const wettest = days.reduce((b, d) => (!b || d.total_in > b.total_in ? d : b), days[0]);
  return (
    <section className="stack-8 rain-section" aria-label="Rain flooding">
      <div className="section-label">Rain flooding · La Jolla, Pacific Beach, Mission Beach</div>
      {risky.length === 0 ? (
        <a className="card card-calm" href="#/map?view=rain">
          <span className="card-body">
            {!wettest || wettest.total_in < 0.05
              ? "No rain in the forecast."
              : `Light rain ${dayLabel(wettest.date)}, about ${wettest.total_in.toFixed(1)} in. Not enough to flood streets.`}
          </span>
          <span className="card-foot"><span>See where rain water collects →</span></span>
        </a>
      ) : (
        <div className="area-grid">
          {heads.map(({ area, day }) => day && (
            <a key={area.name} className="card" href="#/map?view=rain">
              <div className="card-head">
                <span className="card-title">{area.name}</span>
                <StatusPill risk={day.level} />
              </div>
              <div className="card-body">{rainSummary(day.level)}</div>
              <div className="card-foot">
                <span>Heaviest {rainWindow(day)}: about {day.max_6h_in.toFixed(2)} in</span>
                <span>Chance of rain {day.chance_pct}%</span>
              </div>
            </a>
          ))}
        </div>
      )}
    </section>
  );
}

