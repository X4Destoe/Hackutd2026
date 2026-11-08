"""resources: send residents to help that is actually safe and open right now (the State Farm piece). Interface: INTERFACE.md.

Inbound resident texts arrive through messaging, which already calls `resources.route(party_id, text)` for every resident
message, so this module does not register its own inbound handler (that would route each text twice).
"""
from __future__ import annotations

import hashlib
import json
import logging
import math
import threading

from app.modules import impact, scenarios
from app.shared import ids, schemas
from app.shared.config import DATA_DIR
from app.shared.events import bus
from app.shared.store import store

log = logging.getLogger(__name__)
_lock = threading.RLock()

NEED_TYPES = {  # PRD 03 §5, in order of preference
    "shelter": ["shelter", "cbre_help_site", "hotel"],
    "warmth": ["warming_center", "shelter", "cbre_help_site"],
    "claim": ["claim_site"],
    "repair": ["repair_vendor"],
    "food_water": ["shelter", "warming_center"],
}
# Where a resident is when they don't say: a neighborhood inside each scenario's hazard area (demo simplification).
PLACES = {
    "Houston": {"memorial": (29.765, -95.452), "downtown": (29.758, -95.367), "midtown": (29.742, -95.378),
                "heights": (29.790, -95.398), "meyerland": (29.686, -95.462), "galleria": (29.739, -95.461),
                "bellaire": (29.705, -95.459), "energy corridor": (29.780, -95.620)},
    "Dallas": {"oak lawn": (32.812, -96.812), "downtown": (32.780, -96.800), "uptown": (32.800, -96.800),
               "lakewood": (32.820, -96.750), "farmers branch": (32.926, -96.890)},
    "Fort Myers": {"fort myers beach": (26.452, -81.948), "downtown": (26.640, -81.870), "mcgregor": (26.590, -81.890),
                   "cape coral": (26.562, -81.950), "san carlos": (26.470, -81.800)},
}
DEFAULT_PLACE = {"Houston": "memorial", "Dallas": "oak lawn", "Fort Myers": "fort myers beach"}
EMERGENCY = {
    "en": "If anyone needs oxygen or medical help, call 911 now. A coordinator has been alerted.",
    "es": "Si alguien necesita oxígeno o atención médica, llame al 911 ahora. Un coordinador ya fue avisado.",
    "vi": "Nếu có người cần oxy hoặc cấp cứu, hãy gọi 911 ngay. Điều phối viên đã được báo.",
}
FINDING = {
    "en": "We're finding you a safe place; a coordinator will text you shortly.",
    "es": "Estamos buscando un lugar seguro para usted; un coordinador le escribirá pronto.",
    "vi": "Chúng tôi đang tìm nơi an toàn cho bạn; điều phối viên sẽ nhắn tin sớm.",
}
SPOTS = {"en": "spots left", "es": "lugares libres", "vi": "chỗ còn trống"}
MAP = {"en": "Map", "es": "Mapa", "vi": "Bản đồ"}
CLAIM_EXTRA = {"en": "Bring your policy number if you have it.", "es": "Traiga su número de póliza si lo tiene.",
               "vi": "Mang theo số hợp đồng bảo hiểm nếu có."}


def _v(x) -> str:
    return getattr(x, "value", x)


def miles(a: tuple[float, float], b: tuple[float, float]) -> float:
    kx = math.cos(math.radians((a[0] + b[0]) / 2)) * 69.0
    return math.hypot((a[1] - b[1]) * kx, (a[0] - b[0]) * 69.0)


# ---------- sites ----------

def seed() -> None:
    """(Re)load the help sites after a scenario load (store.reset() clears them)."""
    with _lock:
        if not store.resources.count():
            store.resources.put_all(schemas.Resource.model_validate(r) for r in json.loads((DATA_DIR / "resources.json").read_text()))
    refresh_safety()


def _status(r: schemas.Resource, hour: int) -> str:
    if _v(r.status) == "closed":
        return "closed"
    if not impact.site_safe(r.lat, r.lon, r.utility_node_id, hour):
        return "unsafe"
    return "full" if r.used >= r.capacity else "open"


def refresh_safety() -> list[str]:
    """Update every site's status for the current step; re-route referrals at sites that became unsafe. Returns changed ids."""
    hour, city = scenarios.current().step_hour, scenarios.scenario().city
    changed = []
    with _lock:
        for r in store.resources.list(city=city):
            status = _status(r, hour)
            if status != _v(r.status):
                store.resources.put(r.model_copy(update={"status": status}))
                changed.append(r.id)
        for ref in store.referrals.list():
            site = store.resources.get(ref.resource_id) if ref.resource_id else None
            if site and _v(site.status) == "unsafe" and ref.status in ("routed", "rerouted"):
                _reroute(ref, site)
    if changed:
        bus.emit("resources.changed", {"changed_ids": changed})
    return changed


def register_site(resource: schemas.Resource) -> schemas.Resource:
    """Add a help site (actions uses this for OFFER_HELP_SITE: type cbre_help_site)."""
    with _lock:
        site = store.resources.put(resource.model_copy(update={"status": _status(resource, scenarios.current().step_hour)}))
    bus.emit("resources.changed", {"changed_ids": [site.id]})
    return site


# ---------- routing ----------

def _locate(party_id: str, text: str, city: str) -> tuple[float, float]:
    places = PLACES.get(city, {})
    low = text.lower()
    for name, point in places.items():
        if name in low:
            return point
    base = places.get(DEFAULT_PLACE.get(city, ""))
    if base is None:
        b = next(iter(store.buildings.list(city=city)), None)
        base = (b.lat, b.lon) if b else (0.0, 0.0)
    h = hashlib.sha256(party_id.encode()).digest()  # deterministic spread so residents are not stacked on one point
    return base[0] + (h[0] - 128) / 128 * 0.006, base[1] + (h[1] - 128) / 128 * 0.006


def _candidates(needs: list[str], people: int, at: tuple[float, float], exclude: set[str]) -> list[tuple[float, schemas.Resource]]:
    wanted = [t for n in needs for t in NEED_TYPES.get(n, [])]
    city = scenarios.scenario().city
    sites = [r for r in store.resources.list(city=city)
             if r.id not in exclude and _v(r.type) in wanted and _v(r.status) == "open" and r.capacity - r.used >= people]
    return sorted(((miles(at, (r.lat, r.lon)), r) for r in sites), key=lambda x: x[0])


def _maps(r: schemas.Resource) -> str:
    return f"https://www.google.com/maps/dir/?api=1&destination={r.lat:.4f},{r.lon:.4f}"


def _send(party_id: str, purpose: str, facts: dict, language: str, referral_id: str | None, fallback: str) -> None:
    from app.modules import messaging
    try:
        from app.modules import ai
        body = ai.compose(purpose, facts, language)
    except Exception:  # noqa: BLE001 - a reply must always go out
        body = fallback
    messaging.send(party_id, body, "redirect", referral_id=referral_id)


def _tell_site(party_id: str, r: schemas.Resource, dist: float, lang: str, ref_id: str, purpose: str) -> None:
    spots = r.capacity - r.used
    if _v(r.type) == "repair_vendor":
        contact = r.phone or r.address
        _send(party_id, "ack", {"details": f"{r.name}: {contact}"}, lang, ref_id, f"{r.name}: {contact}")
        return
    details = f"{dist:.1f} mi · {r.hours} · {spots} {SPOTS.get(lang, SPOTS['en'])} · {MAP.get(lang, MAP['en'])}: {_maps(r)}"
    if _v(r.type) == "claim_site":
        details += " " + CLAIM_EXTRA.get(lang, CLAIM_EXTRA["en"])
    _send(party_id, purpose, {"site_name": r.name, "address": r.address, "details": details}, lang, ref_id,
          f"Go to {r.name}, {r.address}. {_maps(r)}")


def route(party_id: str, text: str) -> schemas.Referral:
    """Classify the need, pick the nearest open+safe site with room, reserve the spots, text the resident."""
    from app.modules import ai
    party = store.parties.require(party_id)
    need = ai.classify_need(text, party.language)
    lang = need.get("language", "en")
    if lang != party.language:
        store.parties.put(party.model_copy(update={"language": lang}))
    needs, people = [_v(n) for n in need["needs"]], int(need.get("people", 1))
    ref_id = ids.new_id("REF")
    history = []
    if "medical" in needs and need.get("urgent"):
        _send(party_id, "ack", {"details": EMERGENCY.get(lang, EMERGENCY["en"])}, lang, ref_id, EMERGENCY["en"])
        history.append("URGENT medical: told to call 911, coordinator alerted")
    with _lock:
        at = _locate(party_id, text, scenarios.scenario().city)
        options = _candidates(needs, people, at, exclude=set())
        if options:
            dist, site = options[0]
            site = store.resources.put(site.model_copy(update={"used": site.used + people}))
            if site.used >= site.capacity:
                site = store.resources.put(site.model_copy(update={"status": "full"}))
            history.append(f"{scenarios.current().step_hour}h: routed to {site.name} ({dist:.1f} mi), {people} spot(s) reserved")
            ref = schemas.Referral(id=ref_id, party_id=party_id, needs=needs, people=people, summary=need.get("summary", ""),
                                   resource_id=site.id, distance_mi=round(dist, 1), status="routed", history=history)
        else:
            history.append(f"{scenarios.current().step_hour}h: no open, safe site with room for {people}")
            ref = schemas.Referral(id=ref_id, party_id=party_id, needs=needs, people=people, summary=need.get("summary", ""),
                                   status="unrouted", history=history)
        store.referrals.put(ref)
    if ref.status == "routed":
        _tell_site(party_id, site, dist, lang, ref.id, "redirect")
        bus.emit("resources.changed", {"changed_ids": [site.id]})
    elif not (needs == ["medical"] and need.get("urgent")):
        _send(party_id, "ack", {"details": FINDING.get(lang, FINDING["en"])}, lang, ref.id, FINDING["en"])
    bus.emit("referral.changed", {"referral_id": ref.id, "status": ref.status, "resource_id": ref.resource_id})
    return ref


def _reroute(ref: schemas.Referral, old: schemas.Resource) -> None:
    """Called under _lock by refresh_safety when a referral's site became unsafe."""
    store.resources.put(old.model_copy(update={"used": max(0, old.used - ref.people)}))
    party = store.parties.get(ref.party_id)
    lang = party.language if party else "en"
    b = store.resources.require(old.id)
    at = _locate(ref.party_id, "", scenarios.scenario().city)
    options = _candidates(ref.needs, ref.people, at, exclude={old.id})
    hour = scenarios.current().step_hour
    if options:
        dist, site = options[0]
        site = store.resources.put(site.model_copy(update={"used": site.used + ref.people}))
        ref = ref.model_copy(update={"resource_id": site.id, "distance_mi": round(dist, 1), "status": "rerouted",
                                     "history": ref.history + [f"{hour}h: {b.name} became unsafe; rerouted to {site.name}"]})
        store.referrals.put(ref)
        _tell_site(ref.party_id, site, dist, lang, ref.id, "reroute")
    else:
        ref = ref.model_copy(update={"resource_id": None, "distance_mi": None, "status": "unrouted",
                                     "history": ref.history + [f"{hour}h: {b.name} became unsafe; no alternative yet"]})
        store.referrals.put(ref)
        _send(ref.party_id, "ack", {"details": FINDING.get(lang, FINDING["en"])}, lang, ref.id, FINDING["en"])
    bus.emit("referral.changed", {"referral_id": ref.id, "status": ref.status, "resource_id": ref.resource_id})


def register() -> None:
    bus.on("scenario.loaded", lambda _p: seed())
    bus.on("timeline.changed", lambda _p: refresh_safety())


from .routes import router  # noqa: E402

__all__ = ["register", "seed", "refresh_safety", "route", "register_site", "NEED_TYPES", "router"]
