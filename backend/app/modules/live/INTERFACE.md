# live public interface

Import `from app.modules import live`. Real-time hazard feeds for the portfolio's cities, free and keyless.

| Function | Returns |
|---|---|
| `snapshot()` | latest snapshot dict (below). **Never waits for the network**: serves the cache, starts a background refresh when older than 5 min; offline -> last good snapshot on disk (`data/live/cache/last.json`, git-ignored) -> committed real seed (`data/live/seed.json`) |
| `status()` | `{fetched_at, age_seconds, stale, refreshing, states, feeds: {alerts \| forecast:<city> \| gauges:<city>: {as_of, age_seconds, stale, error}}, alert_count, alerts_without_area, gauge_count, cities, sources, errors, notes}`. `stale` = any feed missing or older than 15 min |
| `refresh(block=False)` | force a refresh (scripts: `block=True`) |

Snapshot: `{fetched_at, states, alerts: FeatureCollection (NWS alerts with areas; properties id, event, severity, urgency, certainty,
headline, areaDesc, onset, ends, expires, senderName; plus without_area count), conditions: {city: {hours, from, min_temp_f, max_wind_mph,
max_precip_pct, now_temp_f, now_wind_mph, now, worst}}, gauges: [{site, name, lat, lon, gage_ft, time}], gauges_by_city, feeds: {key: {as_of, error}}, building_gauges: {building_id:
nearest gauge within 5 mi + distance_mi}, sources}`.

Routes: `GET /api/live/status`, `GET /api/live/alerts` (GeoJSON). Event: `live.updated` (payload = status) after each good refresh.
Env: `LIVE_STATES` (default `TX,FL`), `LIVE_FETCH=0` disables fetching (tests).

## Failure behavior
- Feeds fail independently. A failed feed **keeps its last good value and its old `as_of`** and records `error`; only a successful
  response replaces data (a successful empty response clears it). A feed never fetched has `as_of: null`.
- **Consumers treat a stale or missing feed as UNKNOWN, never as "no hazard"** (the live scenario must say "data unavailable").
- Refresh cadence: 5 min after a full success; 60 s after any failure (`RETRY_SECONDS`), never once per request.

## Honest limits (for TASK-050, the live scenario)
- **No free real-time power-outage feed** -> live mode has no outages.
- **NWS alerts have areas and severity, not depths** -> any depth/wind used for money must be a labeled proxy.
- **Gauge height is not flood depth**: each gauge has its own datum (a normal reading can be 60 ft). Do not turn `gage_ft` into water
  at a building without flood-stage thresholds (NWS NWPS `api.water.noaa.gov`, not wired yet). Show it as "nearest gauge: X ft".
- Some NWS alerts only name forecast zones (no polygon); they are counted (`alerts_without_area`), not drawn.
