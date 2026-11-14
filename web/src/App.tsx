import { Suspense, lazy, useEffect, useState } from "react";
import { type Forecast, loadForecast } from "./data";
import { Area } from "./screens/Area";
import { Home } from "./screens/Home";

// The map library is large; load it only when someone opens the map.
const MapScreen = lazy(() => import("./screens/MapScreen").then((m) => ({ default: m.MapScreen })));

// Tiny hash router: #/ (home), #/area/<slug>, #/map. Keeps the site a set of
// static files that any host (Vercel) can serve without server routing.
function useRoute(): string {
  const [route, setRoute] = useState(() => window.location.hash.slice(1) || "/");
  useEffect(() => {
    const onHash = () => {
      setRoute(window.location.hash.slice(1) || "/");
      window.scrollTo(0, 0);
    };
    window.addEventListener("hashchange", onHash);
    return () => window.removeEventListener("hashchange", onHash);
  }, []);
  return route;
}

export function App() {
  const route = useRoute();
  const [forecast, setForecast] = useState<Forecast | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadForecast().then(setForecast).catch((e) => setError(String(e)));
  }, []);

  let screen: JSX.Element;
  if (error) {
    screen = <main className="screen"><h1>Forecast unavailable</h1><p>{error}</p></main>;
  } else if (!forecast) {
    screen = (
      <main className="screen" aria-busy="true">
        <div className="skeleton" style={{ height: 90 }} />
        <div className="skeleton" style={{ height: 130 }} />
        <div className="skeleton" style={{ height: 130 }} />
      </main>
    );
  } else if (route.startsWith("/area/")) {
    const areaSlug = route.slice("/area/".length);
    screen = <Area key={areaSlug} forecast={forecast} areaSlug={areaSlug} />;
  } else if (route === "/map") {
    screen = (
      <Suspense fallback={<main className="screen" aria-busy="true"><div className="skeleton" style={{ height: 420 }} /></main>}>
        <MapScreen forecast={forecast} />
      </Suspense>
    );
  } else {
    screen = <Home forecast={forecast} />;
  }

  const current = route === "/map" ? "map" : route === "/about" ? "about" : "forecast";
  return (
    <div className="app">
      {screen}
      <nav className="nav" aria-label="Main">
        <a href="#/" aria-current={current === "forecast" ? "page" : undefined}>
          <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M3 15c3 0 3-2 6-2s3 2 6 2 3-2 6-2" /><path d="M3 19c3 0 3-2 6-2s3 2 6 2 3-2 6-2" /><path d="M12 3v6M9 6l3 3 3-3" /></svg>
          Forecast
        </a>
        <a href="#/map" aria-current={current === "map" ? "page" : undefined}>
          <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M9 4L3 6v14l6-2 6 2 6-2V4l-6 2-6-2z" /><path d="M9 4v14M15 6v14" /></svg>
          Map
        </a>
        <a href="#/about" aria-current={current === "about" ? "page" : undefined}>
          <svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="9" /><path d="M12 11v6M12 7.5v.5" /></svg>
          How it works
        </a>
      </nav>
    </div>
  );
}
