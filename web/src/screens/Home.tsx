import { SearchBox } from "../components/SearchBox";
import { StatusDot, StatusPill } from "../components/StatusPill";
import {
  type Forecast, type Risk, NWS_URL, dayLabel, headlineDay, riskIndex, slug,
  summary, timeLabel, upcoming, updatedLabel, worse,
} from "../data";

export function Home({ forecast }: { forecast: Forecast }) {
  const areas = forecast.areas.map((a) => ({ ...a, days: upcoming(a.days) }));
  const dates = areas[0]?.days.slice(0, 4).map((d) => d.date) ?? [];
  const worstOn = (date: string): Risk =>
    areas.reduce<Risk>((w, a) => worse(w, a.days.find((d) => d.date === date)?.risk ?? "Low"), "Low");
  const alerts = forecast.nws_alerts.filter((a) => /coastal flood|high surf/i.test(a.event));

  return (
    <main className="screen">
      <div>
        <div className="eyebrow">PB &amp; MB Flood Forecast</div>
        <h1>Is my area at risk this week?</h1>
        <div className="sub">Updated {updatedLabel(forecast.issued_at)}</div>
      </div>

      <SearchBox />

      {areas.map((area) => {
        const day = headlineDay(area.days);
        if (!day) return null;
        const extra: string[] = [];
        if (day.risk !== "Low") extra.push(`Worst: ${dayLabel(day.date)} around ${timeLabel(day.worst_time ?? day.bay_peak_time)}`);
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

      <div className="notice">
        {alerts.length > 0 && (
          <>Official: {alerts.map((a) => `NWS ${a.event}`).join(" and ")} in effect. </>
        )}
        This app is not an official warning. <a href={NWS_URL}>Check the National Weather Service</a>.
      </div>
    </main>
  );
}
