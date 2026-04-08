"""Immich proxy endpoints — search and thumbnail proxying."""

import logging
from datetime import datetime, timedelta, timezone

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response

from config.settings import settings
from src.api.deps import CurrentUser, get_current_user

log = logging.getLogger(__name__)
router = APIRouter()


def _headers() -> dict:
    return {"x-api-key": settings.immich_api_key, "Accept": "application/json"}


@router.get("/immich/search")
def immich_search(
    q: str = Query(..., min_length=1),
    limit: int = Query(20, ge=1, le=50),
    _user: CurrentUser = Depends(get_current_user),
):
    """CLIP-based smart search in Immich."""
    if not settings.immich_api_key:
        return []
    resp = httpx.post(
        f"{settings.immich_url}/api/search/smart",
        json={"query": q, "page": 1, "size": limit},
        headers=_headers(),
        timeout=15,
    )
    resp.raise_for_status()
    assets = resp.json().get("assets", {}).get("items", [])
    return [_summarise(a) for a in assets]


@router.get("/immich/search/recent")
def immich_search_recent(
    days: int = Query(7, ge=1, le=90),
    limit: int = Query(20, ge=1, le=50),
    _user: CurrentUser = Depends(get_current_user),
):
    """Get recent photos from Immich."""
    if not settings.immich_api_key:
        return []
    after = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    resp = httpx.post(
        f"{settings.immich_url}/api/search/metadata",
        json={"takenAfter": after, "order": "desc", "size": limit},
        headers=_headers(),
        timeout=15,
    )
    resp.raise_for_status()
    assets = resp.json().get("assets", {}).get("items", [])
    return [_summarise(a) for a in assets]


@router.get("/immich/asset/{asset_id}/thumbnail")
def immich_thumbnail(
    asset_id: str,
    _user: CurrentUser = Depends(get_current_user),
):
    """Proxy an Immich asset thumbnail."""
    if not settings.immich_api_key:
        raise HTTPException(503, "Immich not configured")
    resp = httpx.get(
        f"{settings.immich_url}/api/assets/{asset_id}/thumbnail",
        headers={"x-api-key": settings.immich_api_key},
        params={"size": "thumbnail"},
        timeout=10,
    )
    if resp.status_code != 200:
        raise HTTPException(404, "Thumbnail not found")
    return Response(
        content=resp.content,
        media_type=resp.headers.get("content-type", "image/jpeg"),
        headers={"Cache-Control": "public, max-age=3600"},
    )


def _summarise(asset: dict) -> dict:
    return {
        "id": asset.get("id"),
        "type": asset.get("type", "IMAGE"),
        "original_filename": asset.get("originalFileName"),
        "created_at": asset.get("fileCreatedAt"),
        "thumbnail_url": f"/api/v1/immich/asset/{asset['id']}/thumbnail",
    }
