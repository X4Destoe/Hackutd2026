import asyncio
import threading

from app.shared.events import EventBus, sse_frame


def test_handlers_run_and_bad_handler_is_isolated():
    bus, seen = EventBus(), []
    bus.on("x", lambda p: 1 / 0)
    bus.on("x", lambda p: seen.append(p["n"]))
    bus.emit("x", {"n": 1}); bus.emit("other", {})
    assert seen == [1]


def test_sse_frame_format():
    assert sse_frame("timeline.changed", {"step_hour": -24}) == 'event: timeline.changed\ndata: {"step_hour": -24}\n\n'


def test_stream_delivers_emits_from_other_threads():
    async def run():
        bus = EventBus()
        gen = bus.stream()
        assert await gen.__anext__() == ": connected\n\n"
        nxt = asyncio.ensure_future(gen.__anext__())
        await asyncio.sleep(0)
        t = threading.Thread(target=bus.emit, args=("plan.changed", {"plan_id": "PLAN-001"})); t.start(); t.join()
        frame = await asyncio.wait_for(nxt, 2)
        await gen.aclose()
        return frame, bus.client_count
    frame, clients = asyncio.run(run())
    assert frame.startswith("event: plan.changed") and '"PLAN-001"' in frame and clients == 0
