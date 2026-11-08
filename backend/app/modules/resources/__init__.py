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
    "en": "If anyone needs oxygen or medical help, call 911 now. Your request is flagged for coordinator follow-up.",
    "es": "Si alguien necesita oxígeno o atención médica, llame al 911 ahora. Su solicitud quedó marcada para seguimiento de un coordinador.",
    "vi": "Nếu có người cần oxy hoặc cấp cứu, hãy gọi 911 ngay. Yêu cầu của bạn đã được đánh dấu để điều phối viên theo dõi.",
}
SHELTER = {  # hurricane-force wind where the resident is: travelling is the danger
    "en": "Hurricane-force winds now: stay where you are, away from windows, on the lowest floor that is not flooding. "
          "Do not travel. We will text you the nearest open, safe site as soon as one opens. If anyone is hurt, call 911.",
    "es": "Vientos huracanados ahora: quédese donde está, lejos de las ventanas, en el piso más bajo que no se esté inundando. "
          "No viaje. Le enviaremos el sitio abierto y seguro más cercano en cuanto haya uno. Si alguien está herido, llame al 911.",
    "vi": "Gió bão mạnh lúc này: ở yên tại chỗ, tránh xa cửa sổ, ở tầng thấp nhất không bị ngập. Đừng di chuyển. "
          "Chúng tôi sẽ nhắn nơi an toàn gần nhất ngay khi có. Nếu có người bị thương, gọi 911.",
}
HURRICANE_FORCE_MPH = 74
FINDING = {
    "en": "We received your request. No open, safe site has room right now; your request is flagged for coordinator follow-up.",
    "es": "Recibimos su solicitud. Ahora no hay un sitio abierto y seguro con espacio; su solicitud quedó marcada para seguimiento de un coordinador.",
    "vi": "Chúng tôi đã nhận yêu cầu. Hiện chưa có nơi an toàn còn chỗ; yêu cầu của bạn đã được đánh dấu để điều phối viên theo dõi.",
}
SPOTS = {"en": "spots left", "es": "lugares libres", "vi": "chỗ còn trống"}
MAP = {"en": "Map", "es": "Mapa", "vi": "Bản đồ"}
REPLY = {  # local, deterministic copy: replies never wait on an LLM (they run inside the timeline handler)
    "redirect": {"en": "Go to {site}, {address}. {details}", "es": "Vaya a {site}, {address}. {details}",
                 "vi": "Hãy đến {site}, {address}. {details}"},
    "reroute": {"en": "Change of plan: {old} is no longer safe. Go to {site}, {address}. {details}",
                "es": "Cambio de plan: {old} ya no es seguro. Vaya a {site}, {address}. {details}",
                "vi": "Thay đổi kế hoạch: {old} không còn an toàn. Hãy đến {site}, {address}. {details}"},
    "contact": {"en": "For emergency repairs contact {site}: {contact}.", "es": "Para reparaciones urgentes contacte a {site}: {contact}.",
                "vi": "Để sửa chữa khẩn cấp, liên hệ {site}: {contact}."},
}
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
    changed, outbox, moved = [], [], []
    with _lock:
        for r in store.resources.list(city=city):
            status = _status(r, hour)
            if status != _v(r.status):
                store.resources.put(r.model_copy(update={"status": status}))
                changed.append(r.id)
        for ref in store.referrals.list():
            site = store.resources.get(ref.resource_id) if ref.resource_id else None
            if site and _v(site.status) == "unsafe" and ref.status in ("routed", "rerouted"):
                ref, ids_ = _reroute(ref, site, outbox)
                moved.append(ref)
                changed += [i for i in ids_ if i not in changed]
        # Residents still waiting (no safe site, no room, or hurricane-force wind): route them as soon as a site opens.
        for ref in sorted(store.referrals.list(status="unrouted"), key=lambda r: r.id):
            options = _candidates(ref.needs, ref.people, _locate(ref.party_id, "", city), exclude=set())
            if not options:
                continue
            dist, site = options[0]
            site = _reserve(site, ref.people)
            party = store.parties.get(ref.party_id)
            lang = party.language if party and party.language in EMERGENCY else "en"
            ref = ref.model_copy(update={"resource_id": site.id, "distance_mi": round(dist, 1), "status": "routed",
                                         "history": ref.history + [f"{hour}h: a safe site opened; routed to {site.name}, "
                                                                   f"{ref.people} spot(s) reserved"]})
            store.referrals.put(ref)
            outbox.append((ref.party_id, _site_text(site, dist, lang, "redirect"), ref.id))
            moved.append(ref)
            changed += [site.id] if site.id not in changed else []
    _flush(outbox)  # texts go out after the lock: a slow channel never stalls the timeline
    if changed:
        bus.emit("resources.changed", {"changed_ids": changed})
    for ref in moved:
        bus.emit("referral.changed", {"referral_id": ref.id, "status": ref.status, "resource_id": ref.resource_id})
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


def _hurricane_force(at: tuple[float, float]) -> bool:
    """Wind physically at the resident's location right now (present reading), not the forecast peak."""
    try:
        return scenarios.hazard_at(at[0], at[1], present=True).get("wind_mph", 0) > HURRICANE_FORCE_MPH
    except Exception:  # noqa: BLE001 - guidance must never break routing
        return False


def _maps(r: schemas.Resource) -> str:
    return f"https://www.google.com/maps/dir/?api=1&destination={r.lat:.4f},{r.lon:.4f}"


Outbox = list[tuple[str, str, str]]  # (party_id, body, referral_id): sent after the lock is released


def _flush(outbox: Outbox) -> None:
    from app.modules import messaging
    for party_id, body, ref_id in outbox:
        messaging.send(party_id, body, "redirect", referral_id=ref_id)


def _site_text(r: schemas.Resource, dist: float, lang: str, purpose: str, old: str = "") -> str:
    lang = lang if lang in ("en", "es", "vi") else "en"
    if _v(r.type) == "repair_vendor":
        return REPLY["contact"][lang].format(site=r.name, contact=r.phone or r.address)
    spots = r.capacity - r.used
    details = f"{dist:.1f} mi · {r.hours} · {spots} {SPOTS[lang]} · {MAP[lang]}: {_maps(r)}"
    if _v(r.type) == "claim_site":
        details += " " + CLAIM_EXTRA[lang]
    body = REPLY[purpose][lang].format(site=r.name, address=r.address, details=details, old=old)
    if len(body) > 320:  # SMS limit: keep the address and the map link, drop the rest
        body = REPLY[purpose][lang].format(site=r.name, address=r.address, details=_maps(r), old=old)
    return body


def _reserve(site: schemas.Resource, people: int) -> schemas.Resource:
    update = {"used": site.used + people}
    if site.used + people >= site.capacity:
        update["status"] = "full"
    return store.resources.put(site.model_copy(update=update))


def route(party_id: str, text: str) -> schemas.Referral:
    """Classify the need, pick the nearest open+safe site with room, reserve the spots, text the resident."""
    from app.modules import ai
    party = store.parties.require(party_id)
    need = ai.classify_need(text, party.language)
    lang = need.get("language", "en")
    if lang not in EMERGENCY:
        lang = "en"
    if lang != party.language:
        store.parties.put(party.model_copy(update={"language": lang}))
    needs, people = [_v(n) for n in need["needs"]], int(need.get("people", 1))
    ref_id = ids.new_id("REF")
    history, outbox, changed = [], [], []
    urgent = "medical" in needs and bool(need.get("urgent"))
    if urgent:
        outbox.append((party_id, EMERGENCY[lang], ref_id))
        history.append("URGENT medical: told to call 911, flagged for coordinator follow-up")
    with _lock:
        hour = scenarios.current().step_hour
        at = _locate(party_id, text, scenarios.scenario().city)
        options = _candidates(needs, people, at, exclude=set())
        if options:
            dist, site = options[0]
            site = _reserve(site, people)
            changed.append(site.id)
            history.append(f"{hour}h: routed to {site.name} ({dist:.1f} mi), {people} spot(s) reserved")
            ref = schemas.Referral(id=ref_id, party_id=party_id, needs=needs, people=people, summary=need.get("summary", ""),
                                   resource_id=site.id, distance_mi=round(dist, 1), status="routed", history=history)
            outbox.append((party_id, _site_text(site, dist, lang, "redirect"), ref_id))
        else:
            windy = _hurricane_force(at)
            history.append(f"{hour}h: no open, safe site with room for {people}"
                           + ("; hurricane-force wind: told to shelter in place, will be routed when a site opens" if windy else ""))
            ref = schemas.Referral(id=ref_id, party_id=party_id, needs=needs, people=people, summary=need.get("summary", ""),
                                   status="unrouted", history=history)
            if not (urgent and needs == ["medical"]):
                outbox.append((party_id, (SHELTER if windy else FINDING)[lang], ref_id))
        store.referrals.put(ref)
    _flush(outbox)
    if changed:
        bus.emit("resources.changed", {"changed_ids": changed})
    bus.emit("referral.changed", {"referral_id": ref.id, "status": ref.status, "resource_id": ref.resource_id})
    return ref


def _reroute(ref: schemas.Referral, old: schemas.Resource, outbox: Outbox) -> tuple[schemas.Referral, list[str]]:
    """Under _lock (refresh_safety): move a referral off a site that became unsafe. Texts go to `outbox`."""
    old = store.resources.put(old.model_copy(update={"used": max(0, old.used - ref.people)}))
    party = store.parties.get(ref.party_id)
    lang = party.language if party and party.language in EMERGENCY else "en"
    options = _candidates(ref.needs, ref.people, _locate(ref.party_id, "", scenarios.scenario().city), exclude={old.id})
    hour = scenarios.current().step_hour
    if options:
        dist, site = options[0]
        site = _reserve(site, ref.people)
        ref = ref.model_copy(update={"resource_id": site.id, "distance_mi": round(dist, 1), "status": "rerouted",
                                     "history": ref.history + [f"{hour}h: {old.name} became unsafe; rerouted to {site.name}"]})
        outbox.append((ref.party_id, _site_text(site, dist, lang, "reroute", old=old.name), ref.id))
        changed = [old.id, site.id]
    else:
        ref = ref.model_copy(update={"resource_id": None, "distance_mi": None, "status": "unrouted",
                                     "history": ref.history + [f"{hour}h: {old.name} became unsafe; no alternative with room"]})
        outbox.append((ref.party_id, FINDING[lang], ref.id))
        changed = [old.id]
    store.referrals.put(ref)
    return ref, changed


def register() -> None:
    bus.on("scenario.loaded", lambda _p: seed())
    bus.on("timeline.changed", lambda _p: refresh_safety())


from .routes import router  # noqa: E402

__all__ = ["register", "seed", "refresh_safety", "route", "register_site", "NEED_TYPES", "router"]
