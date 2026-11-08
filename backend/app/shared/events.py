"""Event bus + Server-Sent Events (docs/prd/02-contracts.md §5, modules/core.md).

    bus.on("timeline.changed", handler)      # handler(payload: dict), runs synchronously in emit()
    bus.emit("timeline.changed", {...})       # also queued to every SSE client as `event: <type>\\ndata: <json>`
"""
from __future__ import annotations

import asyncio
import json
import logging
from collections import defaultdict
from typing import Any, AsyncIterator, Callable

log = logging.getLogger("events")
PING_SECONDS = 15
QUEUE_SIZE = 500


def sse_frame(type_: str, payload: Any) -> str:
    return f"event: {type_}\ndata: {json.dumps(payload, default=_default)}\n\n"


def _default(o: Any) -> Any:
    if hasattr(o, "model_dump"):
        return o.model_dump(mode="json")
    return getattr(o, "value", str(o))


class EventBus:
    def __init__(self):
        self._handlers: dict[str, list[Callable[[dict], None]]] = defaultdict(list)
        self._clients: list[tuple[asyncio.AbstractEventLoop, asyncio.Queue]] = []

    def on(self, type_: str, handler: Callable[[dict], None]) -> None:
        self._handlers[type_].append(handler)

    def clear_handlers(self) -> None:
        self._handlers.clear()

    def emit(self, type_: str, payload: dict | None = None) -> None:
        payload = payload or {}
        for handler in list(self._handlers.get(type_, [])):
            try:
                handler(payload)
            except Exception:  # one bad handler never breaks the emitter
                log.exception("handler for %s failed", type_)
        frame = sse_frame(type_, payload)
        for loop, queue in list(self._clients):
            try:
                loop.call_soon_threadsafe(_offer, queue, frame)  # emit may run in a worker thread
            except RuntimeError:  # loop closed: client gone
                self._drop(queue)

    def subscribe(self) -> asyncio.Queue:
        queue: asyncio.Queue = asyncio.Queue(maxsize=QUEUE_SIZE)
        self._clients.append((asyncio.get_running_loop(), queue))
        return queue

    def _drop(self, queue: asyncio.Queue) -> None:
        self._clients = [(l, q) for l, q in self._clients if q is not queue]

    async def stream(self) -> AsyncIterator[str]:
        """Per-client SSE stream with a `: ping` comment every 15s."""
        queue = self.subscribe()
        try:
            yield ": connected\n\n"
            while True:
                try:
                    yield await asyncio.wait_for(queue.get(), timeout=PING_SECONDS)
                except asyncio.TimeoutError:
                    yield ": ping\n\n"
        finally:
            self._drop(queue)

    @property
    def client_count(self) -> int:
        return len(self._clients)


def _offer(queue: asyncio.Queue, frame: str) -> None:
    if queue.full():  # slow client: drop the oldest frame
        try:
            queue.get_nowait()
        except asyncio.QueueEmpty:
            pass
    queue.put_nowait(frame)


bus = EventBus()
