"""Home Inventory API — FastAPI application."""

import asyncio
import logging
import sys
from contextlib import asynccontextmanager
from pathlib import Path

_project_root = str(Path(__file__).resolve().parent.parent.parent)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config.settings import settings
from src.api.deps import close_pool, init_pool
from src.api.routers import amazon, auth, categories, documents, ebay, export, images, immich, ingest, items, location_types, locations, lookup, stats

from mees_shared.usage_tracker import init_usage_tracker, shutdown_usage_tracker, track_usage_middleware, usage_pageview_router
from mees_shared.dashboard import register_with_dashboard
from mees_shared.spa import mount_spa

STATIC_DIR = Path(_project_root) / "static"

_log = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_pool()
    init_usage_tracker("stuff", settings.usage_dsn)
    task = asyncio.create_task(register_with_dashboard(
        label="Stuff",
        href="https://stuff.mees.st",
        icon="\U0001F4E6",
        sort_order=7,
        registry_key=settings.dash_registry_key,
    ))
    yield
    task.cancel()
    shutdown_usage_tracker()
    close_pool()


app = FastAPI(
    title="Home Inventory API",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.middleware("http")(track_usage_middleware)

# Mount routers
app.include_router(auth.router, prefix="/api/v1", tags=["auth"])
app.include_router(location_types.router, prefix="/api/v1", tags=["location-types"])
app.include_router(categories.router, prefix="/api/v1", tags=["categories"])
app.include_router(locations.router, prefix="/api/v1", tags=["locations"])
app.include_router(items.router, prefix="/api/v1", tags=["items"])
app.include_router(images.router, prefix="/api/v1", tags=["images"])
app.include_router(documents.router, prefix="/api/v1", tags=["documents"])
app.include_router(amazon.router, prefix="/api/v1", tags=["amazon"])
app.include_router(ebay.router, prefix="/api/v1", tags=["ebay"])
app.include_router(lookup.router, prefix="/api/v1", tags=["lookup"])
app.include_router(immich.router, prefix="/api/v1", tags=["immich"])
app.include_router(ingest.router, prefix="/api/v1", tags=["ingest"])
app.include_router(stats.router, prefix="/api/v1", tags=["stats"])
app.include_router(export.router, prefix="/api/v1", tags=["export"])
app.include_router(usage_pageview_router, prefix="/api/v1")

# SPA serving + /health endpoint
mount_spa(app, STATIC_DIR)
