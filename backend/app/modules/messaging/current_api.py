"""Current Photon HTTP API and Standard Webhooks; contracts verified against official
@photon-ai/api 0.6.0 and @photon-ai/convex 0.1.0. No provider request is retried.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import re
import time
import uuid
from urllib.parse import quote

import httpx

from .photon import PhotonError

SHARED_SETUP = "Text the Photon agent number from this phone first, and add this phone under iMessage > senders in app.beta.photon.codes."


class PhotonAPIError(PhotonError):
    def __init__(self, status: int):
        self.status = status
        super().__init__(f"Photon API refused the request ({status}); no automatic retry")

ORIGIN = "https://api.photon.codes"
API_VERSION = "2026-07-01"
E164 = re.compile(r"\+[1-9]\d{7,14}\Z")


def verify(raw: bytes, headers: dict[str, str], secret: str, now: float | None = None) -> bool:
    """Standard Webhooks: sign id.timestamp.raw_body using the decoded whsec key."""
    headers = {k.lower(): v for k, v in headers.items()}
    identity, stamp = headers.get("webhook-id", ""), headers.get("webhook-timestamp", "")
    if not identity or len(identity) > 256 or not re.fullmatch(r"\d{1,12}", stamp):
        return False
    if abs((time.time() if now is None else now) - int(stamp)) > 300:
        return False
    try:
        key = base64.b64decode(secret.removeprefix("whsec_"), validate=True)
    except (ValueError, TypeError):
        return False
    if not key:
        return False
    expected = base64.b64encode(hmac.new(key, identity.encode() + b"." + stamp.encode() + b"." + raw, hashlib.sha256).digest()).decode()
    return any(version == "v1" and re.fullmatch(r"[A-Za-z0-9+/]+={0,2}", signature) and hmac.compare_digest(signature, expected)
               for token in headers.get("webhook-signature", "").split()
               for version, separator, signature in [token.partition(",")] if separator)


def parse(raw: bytes, headers: dict[str, str], config) -> tuple[str, str, list[str]] | None:
    from .photon import _urls
    secret = config.photon_webhook_secret.get_secret_value() or config.spectrum_webhook_secret
    if not verify(raw, headers, secret):
        raise PermissionError("invalid Photon signature or timestamp")
    if len(raw) > 1048576:
        raise ValueError("Photon webhook body is too large")
    event = json.loads(raw)
    if not isinstance(event, dict) or event.get("apiVersion") != API_VERSION:
        raise ValueError("unsupported Photon event API version")
    if not isinstance(event.get("type"), str):
        raise ValueError("Photon event type is required")
    if event["type"] != "message.received":
        return None
    data = event.get("data")
    message = data.get("object") if isinstance(data, dict) else None
    if not isinstance(message, dict) or not isinstance(message.get("id"), str) or not message["id"]:
        raise ValueError("Photon message identity is required")
    if not config.photon_project_id or message.get("projectId") != config.photon_project_id:
        raise PermissionError("Photon event belongs to a different project")
    if message.get("platform") != config.photon_platform or message.get("status") != "received":
        return None
    space, sender, content = message.get("space"), message.get("sentBy"), message.get("content")
    if not all(isinstance(value, dict) for value in [space, sender, content]):
        raise ValueError("malformed Photon message")
    if space.get("kind") != "direct":  # no private management answers into group conversations
        return None
    phone = sender.get("handle")
    if not isinstance(phone, str) or not E164.fullmatch(phone):
        raise ValueError("Photon sender must have an E.164 phone handle")
    if content.get("type") in ["message.read", "space.typing.update"]:
        return None
    text = content.get("text", "")
    if not isinstance(text, str):
        raise ValueError("Photon text must be a string")
    return phone, text, [] if content.get("type") == "text" else _urls(content)


class CurrentPhoton:
    def __init__(self, config, client: httpx.Client | None = None):
        from .photon import PhotonError
        if not config.photon_api_key.get_secret_value() or not re.fullmatch(r"pho_prj_[a-z0-9]+", config.photon_project_id):
            raise PhotonError("Photon API key and project ID must be configured")
        self.config, self.client = config, client
        self.root = ORIGIN + "/v1/projects/" + config.photon_project_id

    def request(self, method: str, suffix: str, *, body=None, params=None, idempotency=None):
        from .photon import PhotonError
        headers = {"Authorization": "Bearer " + self.config.photon_api_key.get_secret_value()}
        if idempotency:
            headers["Idempotency-Key"] = idempotency
        try:
            if self.client is None:
                with httpx.Client(timeout=10, follow_redirects=False) as client:
                    response = client.request(method, self.root + suffix, headers=headers, json=body, params=params)
            else:
                response = self.client.request(method, self.root + suffix, headers=headers, json=body, params=params)
        except httpx.HTTPError as exc:
            # Never serialize provider errors: they may contain credentials or message contents.
            raise PhotonError("Photon API unreachable; send outcome is unknown. Do not retry automatically." if suffix == "/messages" else "Photon API unreachable before message send.") from exc
        if response.status_code not in [200, 201, 202]:
            raise PhotonAPIError(response.status_code)
        try:
            data = response.json()
        except ValueError as exc:
            raise PhotonError("Photon API returned an invalid response") from exc
        if not isinstance(data, dict):
            raise PhotonError("Photon API returned an invalid response")
        return response.status_code, data

    def agents(self) -> dict[str, dict]:
        if self.config.photon_sender_id:
            _, user = self.request("GET", "/users/" + quote(self.config.photon_sender_id, safe=""))
            users = [user]
        else:
            users, token = [], None
            for _ in range(10):
                _, page = self.request("GET", "/users", params={"platform": self.config.photon_platform, "pageSize": 100, **({"pageToken": token} if token else {})})
                if not isinstance(page.get("items"), list):
                    raise PhotonError("Photon sender discovery returned an invalid response")
                users.extend(page["items"])
                token = page.get("nextPageToken")
                if not token:
                    break
            if token:
                raise PhotonError("Set PHOTON_SENDER_ID to select a sending identity explicitly")
        # Shared Agents have no resourceId: Photon enforces the assignment and inbound-first policy.
        return {u["id"]: u for u in users if isinstance(u, dict) and u.get("projectId") == self.config.photon_project_id
                and u.get("platform") == self.config.photon_platform and isinstance(u.get("id"), str) and u["id"]
                and isinstance(u.get("details"), dict) and (u["details"].get("resourceId") or u["details"].get("type") == "shared")}

    def sender(self) -> str:
        agents = self.agents()
        if len(agents) != 1:
            raise PhotonError("Configure PHOTON_SENDER_ID for one available sending identity; no line was provisioned automatically")
        return next(iter(agents))

    def conversation(self, phone: str, recipient: str, agents: dict[str, dict]) -> tuple[str, str] | None:
        token, matches = None, []
        for _ in range(10):
            _, page = self.request("GET", "/spaces", params={"platform": self.config.photon_platform, "participantHandle": phone,
                "pageSize": 100, **({"pageToken": token} if token else {})})
            if not isinstance(page.get("items"), list):
                raise PhotonError("Photon conversation lookup returned an invalid response")
            for space in page["items"]:
                if not isinstance(space, dict) or space.get("projectId") != self.config.photon_project_id or space.get("platform") != self.config.photon_platform or space.get("kind") != "direct":
                    continue
                participants = space.get("participantIds")
                if not isinstance(participants, list) or len(participants) != 2 or not all(isinstance(p, str) for p in participants) or recipient not in participants:
                    continue
                other = next((p for p in participants if p != recipient), None)
                if other in agents and isinstance(space.get("id"), str) and space["id"]:
                    matches.append((other, space["id"]))
            token = page.get("nextPageToken")
            if not token:
                break
        if token:
            raise PhotonError("Conversation lookup exceeded its page limit; select a sender explicitly")
        if len({m[0] for m in matches}) > 1:
            raise PhotonError("More than one sending identity has a conversation with this recipient; set PHOTON_SENDER_ID")
        return matches[0] if matches else None

    def send(self, phone: str, text: str) -> str:
        allowed = {pair.strip().rpartition(":")[0] for pair in self.config.demo_phones.split(",") if ":" in pair}
        if not E164.fullmatch(phone) or phone not in allowed:
            raise PhotonError("Recipient is not listed in DEMO_PHONES")
        if not text.strip() or len(text) > 2000:
            raise PhotonError("Photon text must contain 1–2000 characters")
        agents = self.agents()
        if not agents:
            raise PhotonError("No available Photon Agent identity was found. " + SHARED_SETUP)
        _, recipient = self.request("POST", "/users", body={"platform": self.config.photon_platform, "handle": phone})
        if recipient.get("projectId") != self.config.photon_project_id or recipient.get("platform") != self.config.photon_platform or recipient.get("handle") != phone or not isinstance(recipient.get("id"), str) or not recipient["id"]:
            raise PhotonError("Photon recipient identity was not confirmed")
        existing = self.conversation(phone, recipient["id"], agents)
        key = str(uuid.uuid4())
        if existing:
            sender, space_id = existing
        else:
            if len(agents) != 1:
                raise PhotonError("Set PHOTON_SENDER_ID to select one sending identity")
            sender = next(iter(agents))
            if agents[sender]["details"].get("type") == "shared":
                raise PhotonError(SHARED_SETUP)
            try:
                _, space = self.request("POST", "/spaces", body={"platform": self.config.photon_platform, "participantIds": [sender, recipient["id"]]}, idempotency=key + "-space")
            except PhotonAPIError as exc:
                if exc.status in [403, 404, 422]:
                    raise PhotonError(SHARED_SETUP) from None
                raise
            if space.get("projectId") != self.config.photon_project_id or space.get("platform") != self.config.photon_platform or space.get("kind") != "direct" or not isinstance(space.get("participantIds"), list) or not all(isinstance(p, str) for p in space["participantIds"]) or not {sender, recipient["id"]}.issubset(space["participantIds"]) or not isinstance(space.get("id"), str) or not space["id"]:
                raise PhotonError("Photon conversation identity was not confirmed")
            space_id = space["id"]
        status, message = self.request("POST", "/messages", body={"senderId": sender, "spaceId": space_id, "content": {"type": "text", "format": "plain", "text": text}}, idempotency=key + "-message")
        if status != 202 or message.get("projectId") != self.config.photon_project_id or message.get("status") not in ["dispatched", "accepted", "delivered"] or not isinstance(message.get("id"), str) or not message["id"]:
            raise PhotonError("Photon did not acknowledge the message; delivery is not confirmed")
        return message["id"]
