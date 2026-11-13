# Project: PB & MB Flood Forecast

## Who I am
I'm Brandon, a CS senior at SDSU (graduating Dec 2026). I surf in San Diego most
mornings. This is a showcase project for a Surfline internship application,
aimed at Surfline's Coastal Intelligence team (they sell wave run-up and
overtopping monitoring to cities). Code goes on my GitHub (BrandonSosa3).
I'm on an Apple Silicon Mac.

## How I want you to work with me
- ONE step at a time. After each step, stop and wait for me to confirm before
  moving on. I'll have questions.
- Explain simply. Define new terms before using them. Use concrete examples.
- Tell me how each step fits the bigger picture.
- I'm new to geospatial data and coastal science; don't assume I know
  GeoPandas, LiDAR, map libraries, or NOAA APIs.
- Before building any screen, show me a simple sketch or description of the
  layout and get my OK.

## What we're building
A tool that predicts, street by street, when and where ocean and bay water
will flood Pacific Beach and Mission Beach this El Nino winter, tested
against real past floods.

Why now: a Kelvin wave and El Nino raised local sea level. On Oct 27, 2026 the
NOAA San Diego gauge (Broadway Pier) peaked at 8.52 ft, more than 1 ft above
predicted, and Mission Bay streets flooded (Bayside Walk berm broke Oct 26).
Scripps expects very high king tides around Christmas. Big El Nino surf can
push water over the Mission Beach / PB boardwalk.

Core idea: Water height = predicted tide + extra water + wave run-up.
- Predicted tide: NOAA tide predictions.
- Extra water: measured minus predicted water level (Kelvin wave, El Nino,
  storms add to this).
- Wave run-up: how far up the beach a wave's water rushes after breaking.
  Estimate with a standard empirical formula (e.g. Stockdon 2006) from wave
  height, wave period, and beach slope. Ocean side only.
Flooding happens where water height exceeds the berm / seawall / boardwalk /
street elevation, and only where water can actually connect to that low spot.

Study area (nothing east of the bay):
- Ocean side: Ocean Front Walk (boardwalk), Mission Beach seawall,
  Crystal Pier area
- Bay side: Bayside Walk, Santa Clara Point, El Carmel Point,
  Sail Bay / Crown Point

## Data (free and public only)
- NOAA Tides & Currents: San Diego 9410170 and La Jolla 9410230 gauges,
  predicted + observed water levels, decades of history
- CDIP buoys and CDIP nearshore wave model (Scripps): wave height/period/direction
- NOAA high-resolution LiDAR elevation: streets, berms, seawall, boardwalk
- OpenStreetMap or SanGIS: building outlines and streets
- National Weather Service archives: past coastal flood / high surf warnings
- News reports/photos (and possibly city Get It Done open data) for real
  flood events to test against
- My own tripod footage (Phase 6 only)
Never use Surfline data, cams, or footage.

## Phases (in order)
1. Measure extra water: download NOAA predicted + observed water levels,
   compute the difference, chart it over time; compare with 1997-98 and
   2015-16 El Ninos.
2. Danger heights + flood map: from elevation data, compute the water level
   at which each street segment and building lot floods (with water
   connectivity, not every low dip). Interactive map with a water-level
   slider, buttons for past floods (e.g. Oct 27, 2026) and today's forecast
   peak, live counts (e.g. "At 8.5 ft: 140 buildings, 2.1 miles of street"),
   and a 3D view where a water surface rises through the neighborhood.
3. Backtest: 10-20 past days (real floods + near misses, including Feb 2023,
   the New Year's 2024 big-wave events, Oct 26-27 2026). Honest score card:
   hits, misses, false alarms.
4. Live 3-day forecast: tide forecast + current extra water + CDIP wave
   forecast -> green/yellow/red per area. Log every forecast before the event
   and check it after, especially through the December king tides.
5. Polish: final website, 60-90 sec demo video, short write-up (method,
   accuracy, limits, and how it differs from USGS CoSMoS / NOAA maps, which
   mostly show long-term sea level rise).
6. LAST, bonus: phone on a tripod at a fixed spot during king tides; computer
   vision finds the water line in each frame and measures its height against
   a fixed marker, to compare with the forecast.

## Design rules (non-negotiable)
This must NOT feel like a government flood map. It should feel like a
polished consumer weather app: easy, calm, nice to look at, with deep data
available on demand.
- First screen answers one question: "Is my area at risk this week?" Big,
  simple status per area (e.g. "Mission Beach: Moderate risk Thu 8am").
- Plain language on the main screen. No jargon (no "MLLW", "run-up exceeds
  crest"). Technical terms only in detail views, always explained.
- Clean, muted basemap, smooth animations, few layers at once.
- Detail on demand: tap a street, area, or day to see numbers, charts, and
  how the prediction was made.
- Mobile-first, then desktop.
- Address/street search that jumps to that spot.
- Architecture: a Python data pipeline does the heavy computation and saves
  results as files; the website (React + MapLibre, deck.gl for 3D) only
  displays them, so it stays fast.

## Rules
- Map says "water reaches this property," never "this house floods" (floor
  heights are unknown). Show building shapes only, no addresses or owner
  names on the map.
- Site says it is not an official warning and points to the National Weather
  Service.
- Keep code clean and readable; record the source and date of every dataset.

## Priorities
- No deadline. Quality over speed: don't cut corners or drop features to save
  time. All phases are in scope, including the 3D view, 1997-98 comparison,
  December king tide validation, and Phase 6 tripod.
- Start the automated forecast logger early (right after Phase 1) so it builds
  a long, honest track record that includes the December king tides.
- Hosting: website on Vercel (Brandon has a Pro account). GitHub repo stays
  private until Phase 2 looks good, then goes public.

## Where we are right now
- Plan approved. Folder set up; private repo BrandonSosa3/pb-mb-flood-forecast.
- Phase 1 mostly done: 45-day 6-min chart, 1980-2026 hourly history for
  San Diego + La Jolla, El Nino comparison, two-gauge check.
  Key results (Nov 13, 2026): extra water above normal ~+1.1-1.2 ft (Oct-Nov),
  about 2x any month since 1980; Oct 27 2026 = highest hour on record at both
  gauges; gauges agree (corr 0.91). Oct-Nov data still NOAA-preliminary.
- Open question: baseline trend differs (SD +0.09 vs LJ +0.05 ft/decade).
- Next: start the automated daily forecast logger before Dec king tides.
- Next step: set up this project folder (git, Python environment, folder
  structure), then write a script that downloads NOAA predicted + observed
  water levels for San Diego 9410170 for the past month and computes the
  extra water, so we can see the Oct 27 spike.
- Begin with the folder setup, explained simply. One step at a time.
