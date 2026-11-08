"""App composition root (docs/prd/modules/core.md).

Every package under app/modules/ is discovered automatically: its `router` (if any) is mounted under /api and its
`register()` (if any) is called. Feature modules never edit this file.
"""
from __future__ import annotations

import importlib
import logging
import pkgutil
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import create_model

from app import modules as modules_pkg
from app.shared import schemas
from app.shared.events import bus

log = logging.getLogger("app")

# One model with every shared schema as an optional field, so /openapi.json (and generated frontend types)
# include all contract types even before their owners' routes exist.
Contracts = create_model("Contracts", **{m.__name__: (Optional[m], None) for m in schemas.ALL_MODELS})


def discover_modules() -> list:
    found = []
    for info in sorted(pkgutil.iter_modules(modules_pkg.__path__), key=lambda i: i.name):
        if info.name.startswith("_"):
            continue
        try:
            found.append(importlib.import_module(f"app.modules.{info.name}"))
        except Exception:
            log.exception("module %s failed to import; skipping", info.name)
    return found


def create_app() -> FastAPI:
    bus.clear_handlers()
    mods = discover_modules()

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        scenarios = next((m for m in mods if m.__name__.endswith(".scenarios")), None)
        if scenarios and callable(getattr(scenarios, "load", None)):  # start with the default scenario loaded
            from app.shared.config import settings
            scenarios.load(settings.default_scenario)
        yield

    app = FastAPI(title="Operation Storm API", version="0.1.0", lifespan=lifespan)
    app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

    @app.exception_handler(KeyError)
    async def not_found(_: Request, exc: KeyError):
        return JSONResponse(status_code=404, content={"detail": str(exc).strip("'\"")})

    @app.get("/api/health", tags=["core"])
    def health() -> dict:
        return {"ok": True}

    @app.get("/api/events", tags=["core"])
    async def events():
        return StreamingResponse(bus.stream(), media_type="text/event-stream",
                                 headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})

    @app.get("/api/_contracts", response_model=Contracts, tags=["core"])
    def contracts():
        return Contracts()

    for mod in mods:
        if getattr(mod, "router", None) is not None:
            app.include_router(mod.router, prefix="/api")
    for mod in mods:
        if callable(getattr(mod, "register", None)):
            mod.register()
    app.state.modules = [m.__name__.rsplit(".", 1)[-1] for m in mods]
    return app


app = create_app()
