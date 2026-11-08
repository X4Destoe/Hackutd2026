"""Fetch and parse the free real-time feeds. Pure functions over an httpx.Client so tests run offline (MockTransport).

Sources (no API keys; verified 2026-11-08):
  NWS alerts     https://api.weather.gov/alerts/active?area=TX,FL         GeoJSON polygons (some alerts only name zones)
  NWS forecast   https://api.weather.gov/points/{lat},{lon} -> forecastHourly
  USGS gauges    https://waterservices.usgs.gov/nwis/iv/?bBox=...&parameterCd=00065   gage height (ft), stream sites
There is no free real-time power-outage feed, so live mode has no outages (said in status, never faked).
"""
from __future__ import annotations

import math
import re
from datetime import datetime, timezone

import httpx

USER_AGENT = "OperationStorm/0.1 (HackUTD hackathon demo)"
NWS = "https://api.weather.gov"
USGS = "https://waterservices.usgs.gov/nwis/iv/"
ALERT_FIELDS = ("id", "event", "severity", "urgency", "certainty", "headline", "areaDesc", "onset", "ends", "expires", "senderName")


def client(timeout: float = 15.0) -> httpx.Client:
    return httpx.Client(headers={"User-Agent": USER_AGENT, "Accept": "application/geo+json, application/json"}, timeout=timeout)


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


# ---------- NWS alerts ----------

def fetch_alerts(c: httpx.Client, states: list[str]) -> dict:
    r = c.get(f"{NWS}/alerts/active", params={"area": ",".join(states)})
    r.raise_for_status()
    return parse_alerts(r.json())


def parse_alerts(data: dict) -> dict:
    """Keep alerts that have a drawable area; trim properties to what the app shows."""
    features = []
    for f in data.get("features", []):
        if not f.get("geometry"):
            continue
        p = f.get("properties", {})
        features.append({"type": "Feature", "geometry": f["geometry"], "properties": {k: p.get(k) for k in ALERT_FIELDS}})
    return {"type": "FeatureCollection", "features": features,
            "without_area": sum(1 for f in data.get("features", []) if not f.get("geometry"))}


# ---------- NWS hourly forecast ----------

def parse_wind_mph(text: str | None) -> float:
    """'5 mph' -> 5, '10 to 20 mph' -> 20 (the upper bound)."""
    nums = [float(n) for n in re.findall(r"\d+(?:\.\d+)?", text or "")]
    return max(nums) if nums else 0.0


def fetch_forecast(c: httpx.Client, lat: float, lon: float, hourly_url: str | None = None) -> tuple[dict, str]:
    """Returns (summary, forecastHourly URL). Pass the URL back next time to skip the /points lookup."""
    if not hourly_url:
        r = c.get(f"{NWS}/points/{lat:.4f},{lon:.4f}")
        r.raise_for_status()
        hourly_url = r.json()["properties"]["forecastHourly"]
    r = c.get(hourly_url)
    r.raise_for_status()
    return parse_forecast(r.json()), hourly_url


def parse_forecast(data: dict, hours: int = 48) -> dict:
    periods = data.get("properties", {}).get("periods", [])[:hours]
    if not periods:
        return {}
    temps = [p["temperature"] if p.get("temperatureUnit", "F") == "F" else p["temperature"] * 9 / 5 + 32 for p in periods]
    winds = [parse_wind_mph(p.get("windSpeed")) for p in periods]
    rain = [((p.get("probabilityOfPrecipitation") or {}).get("value") or 0) for p in periods]
    worst = max(range(len(periods)), key=lambda i: (winds[i], rain[i]))
    return {"hours": len(periods), "from": periods[0]["startTime"], "min_temp_f": min(temps), "max_wind_mph": max(winds),
            "max_precip_pct": max(rain), "now_temp_f": temps[0], "now_wind_mph": winds[0],
            "now": periods[0].get("shortForecast", ""), "worst": periods[worst].get("shortForecast", "")}


# ---------- USGS stream gauges ----------

def fetch_gauges(c: httpx.Client, bbox: tuple[float, float, float, float]) -> list[dict]:
    west, south, east, north = bbox
    r = c.get(USGS, params={"format": "json", "bBox": f"{west:.3f},{south:.3f},{east:.3f},{north:.3f}", "parameterCd": "00065",
                            "siteType": "ST", "siteStatus": "active"})
    if r.status_code == 404:  # USGS answers 404 when no site matches
        return []
    r.raise_for_status()
    return parse_gauges(r.json())


def parse_gauges(data: dict) -> list[dict]:
    out = []
    for ts in data.get("value", {}).get("timeSeries", []):
        info, values = ts["sourceInfo"], (ts.get("values") or [{}])[0].get("value") or []
        if not values:
            continue
        geo = info["geoLocation"]["geogLocation"]
        try:
            height = float(values[-1]["value"])
        except (TypeError, ValueError):
            continue
        if height <= -999:  # USGS no-data sentinel
            continue
        out.append({"site": info["siteCode"][0]["value"], "name": info["siteName"], "lat": geo["latitude"], "lon": geo["longitude"],
                    "gage_ft": height, "time": values[-1]["dateTime"]})
    return out


def miles(a: tuple[float, float], b: tuple[float, float]) -> float:
    """Miles between two (lat, lon) points (equirectangular, fine at city scale)."""
    kx = math.cos(math.radians((a[0] + b[0]) / 2)) * 69.0
    return math.hypot((a[1] - b[1]) * kx, (a[0] - b[0]) * 69.0)
