"""Home Inventory API — FastAPI application."""

import sys
from contextlib import asynccontextmanager
from pathlib import Path

_project_root = str(Path(__file__).resolve().parent.parent.parent)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from config.settings import settings
from src.api.deps import close_pool, init_pool
from src.api.routers import amazon, auth, categories, documents, ebay, export, images, immich, ingest, items, location_types, locations, lookup, stats
from src.api.usage_tracker import init_usage_tracker, shutdown_usage_tracker, track_usage_middleware, usage_pageview_router

STATIC_DIR = Path(_project_root) / "static"


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_pool()
    init_usage_tracker("stuff", settings.usage_dsn)
    yield
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


@app.get("/health")
def health():
    return {"status": "ok"}


# Serve React SPA
if STATIC_DIR.is_dir():
    app.mount("/assets", StaticFiles(directory=STATIC_DIR / "assets"), name="static-assets")

    @app.get("/{full_path:path}")
    async def serve_spa(request: Request, full_path: str):
        file_path = STATIC_DIR / full_path
        if full_path and file_path.is_file():
            return FileResponse(file_path)
        return FileResponse(STATIC_DIR / "index.html")
