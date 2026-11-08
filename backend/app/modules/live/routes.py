"""HTTP routes for live data. Mounted under /api by app.main."""
from fastapi import APIRouter

import app.modules.live as live

router = APIRouter(tags=["live"])


@router.get("/live/status")
def live_status() -> dict:
    live.snapshot()  # loads from disk / starts a refresh if due; never waits for the network
    return live.status()


@router.get("/live/alerts")
def live_alerts() -> dict:
    """Active NWS alerts with areas, as GeoJSON (properties: event, severity, headline, areaDesc, onset, ends...)."""
    alerts = live.snapshot().get("alerts") or {}
    return {"type": "FeatureCollection", "features": alerts.get("features", [])}
