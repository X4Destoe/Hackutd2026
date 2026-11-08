# live

Real-time feeds: NWS active alerts + hourly forecasts (api.weather.gov), USGS stream gauges (waterservices.usgs.gov).
- `feeds.py`: fetch + parse (pure, httpx). `__init__.py`: cache, background refresh, disk fallback, status. `routes.py`: HTTP.
- Tests run offline from recorded real responses in `tests/fixtures/`: `cd backend && python -m pytest app/modules/live`.
- Refresh the committed seed: `python -c "import json; from app.modules import live; from app.modules.live import feeds; c=feeds.client(); s,e=live.build_snapshot(c, json.load(open('data/portfolio.json'))); json.dump(s, open('data/live/seed.json','w'))"` (from `backend/`).
