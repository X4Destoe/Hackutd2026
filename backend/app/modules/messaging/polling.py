"""Receive real Photon replies on a laptop without a public webhook or tunnel (TASK-086).

Polls GET /v1/projects/{id}/messages?direction=received every few seconds, as Photon's own first-agent example does
(docs/beta/get-started/imessage). List results are eventually consistent, so each poll re-reads a sliding window
(default 2 minutes, never earlier than when polling started) and de-duplicates by Photon message ID. The dedupe keys are
shared with the signed webhook path, so one message arriving both ways runs once.

Contract (used by live.py):
    poller = PhotonPoller(config); poller.start(); ...; poller.stop()
    poller.error -> None while healthy, else a short reason without secrets or phone numbers.
    poller.poll_once() -> number of new messages delivered (tests and one-shot checks).
Nothing here sends a message or logs keys, phone numbers or message text.
"""
from __future__ import annotations

import logging
import threading
import time
from collections import OrderedDict
from datetime import datetime, timezone

import httpx

from app.shared.store import store

from .current_api import E164, CurrentPhoton
from .photon import PhotonError, _urls

log = logging.getLogger("messaging.polling")

IGNORED_CONTENT = {"message.read", "space.typing.update"}
MAX_PAGES = 5          # per poll: 500 messages in the window is far beyond a demo
MAX_REMEMBERED = 5000  # message IDs kept for local dedupe


def _iso(epoch: float) -> str:
    return datetime.fromtimestamp(epoch, timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _epoch(value) -> float | None:
    if not isinstance(value, str):
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp()
    except ValueError:
        return None


def inbound(message, config) -> tuple[str, str, list[str]] | None:
    """A listed Photon message -> (phone, text, media) when it is a human's reply in a direct conversation, else None.
    Mirrors the checks current_api.parse applies to a verified webhook event."""
    if not isinstance(message, dict) or not isinstance(message.get("id"), str) or not message["id"]:
        return None
    if message.get("projectId") != config.photon_project_id or message.get("platform") != config.photon_platform:
        return None
    if message.get("status") != "received":
        return None
    space, sender, content = message.get("space"), message.get("sentBy"), message.get("content")
    if not all(isinstance(value, dict) for value in (space, sender, content)):
        return None
    if space.get("kind") != "direct" or sender.get("kind") not in (None, "human"):
        return None
    phone = sender.get("handle")
    if not isinstance(phone, str) or not E164.fullmatch(phone):
        return None
    if content.get("type") in IGNORED_CONTENT:
        return None
    text = content.get("text", "")
    if not isinstance(text, str):
        return None
    return phone, text, [] if content.get("type") == "text" else _urls(content)


class PhotonPoller:
    def __init__(self, config, client: httpx.Client | None = None, interval: float = 2.0, window: float = 120.0,
                 clock=time.time):
        self.api = CurrentPhoton(config, client)  # raises PhotonError when the key or project ID is missing
        self.config, self.interval, self.window, self.clock = config, interval, window, clock
        self.started_at = clock() - 5  # a reply sent just before startup still counts; older history never replays
        self._seen: OrderedDict[str, None] = OrderedDict()
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self.error: str | None = None
        self.last_ok: float | None = None

    # ---- one poll ----
    def poll_once(self) -> int:
        since = max(self.started_at, self.clock() - self.window)
        params = {"direction": "received", "platform": self.config.photon_platform, "createdSince": _iso(since),
                  "order": "asc", "pageSize": 100}
        delivered, token = 0, None
        for _ in range(MAX_PAGES):
            _, page = self.api.request("GET", "/messages", params={**params, **({"pageToken": token} if token else {})})
            items = page.get("items")
            if not isinstance(items, list):
                raise PhotonError("Photon message list returned an invalid response")
            for message in items:
                delivered += self._deliver(message, since)
            token = page.get("nextPageToken")
            if not token:
                break
        self.error, self.last_ok = None, self.clock()
        return delivered

    def _deliver(self, message, since: float) -> int:
        from app.modules import messaging
        parsed = inbound(message, self.config)
        created = _epoch(message.get("createdAt")) if isinstance(message, dict) else None
        if parsed is None or (created is not None and created < self.started_at):
            return 0
        mid = message["id"]
        if mid in self._seen:
            return 0
        self._seen[mid] = None
        while len(self._seen) > MAX_REMEMBERED:
            self._seen.popitem(last=False)
        key = f"message:{mid}"  # same key the signed webhook path records
        with messaging._lock:
            if key in messaging._seen_webhook_ids:
                return 0
            messaging._seen_webhook_ids.append(key)
            del messaging._seen_webhook_ids[:-1000]
        phone, text, media = parsed
        party = messaging.party_for_phone(phone)
        if not party.demo_live:  # they reached us over Photon, so replies go back over Photon
            party = store.parties.put(party.model_copy(update={"demo_live": True}))
        messaging.receive(party, text, media)
        return 1

    # ---- background loop ----
    def start(self) -> "PhotonPoller":
        if self._thread is None or not self._thread.is_alive():
            self._stop.clear()
            self._thread = threading.Thread(target=self._run, name="photon-poller", daemon=True)
            self._thread.start()
        return self

    def stop(self, timeout: float = 5.0) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout)

    def _run(self) -> None:
        wait = self.interval
        while not self._stop.is_set():
            try:
                self.poll_once()
                wait = self.interval
            except PhotonError as exc:
                self.error = f"Photon reply polling failed: {exc}"
                wait = min(wait * 2, 30.0)  # back off while Photon is unreachable or refusing; never give up
                log.warning("Photon reply polling failed; retrying in %.0fs", wait)
            except Exception:  # noqa: BLE001 - one bad message must not stop replies for the whole demo
                self.error = "Photon reply polling hit an unexpected error; see the backend log"
                log.exception("Photon reply polling failed unexpectedly")
                wait = min(wait * 2, 30.0)
            self._stop.wait(wait)
