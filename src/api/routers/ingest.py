"""Pipeline ingest endpoint — creates items from barcode scans."""

import logging

from fastapi import APIRouter, Depends, HTTPException, Request

from config.settings import settings
from src.api.deps import get_conn
from src.api.routers.images import download_cover_image

log = logging.getLogger(__name__)
router = APIRouter()


def _verify_pipeline_secret(request: Request) -> None:
    secret = request.headers.get("X-Pipeline-Secret", "")
    if not settings.pipeline_secret or secret != settings.pipeline_secret:
        raise HTTPException(403, "Invalid pipeline secret")


@router.post("/ingest", status_code=201)
def ingest_item(
    request: Request,
    body: dict,
    conn=Depends(get_conn),
    _auth=Depends(_verify_pipeline_secret),
):
    """Create an item from pipeline barcode processing.

    Expected body:
        name (required), barcode, brand, category, description,
        media_type, media_title, media_creator, media_year,
        media_isbn, media_cover_url, media_genre,
        immich_asset_id (optional — links barcode photo to item)
    """
    name = (body.get("name") or "").strip()
    if not name:
        raise HTTPException(400, "name is required")

    cur = conn.cursor()

    # Check for duplicate barcode
    barcode = body.get("barcode")
    if barcode:
        cur.execute("SELECT id, name FROM item WHERE barcode = %s", (barcode,))
        existing = cur.fetchone()
        if existing:
            log.info("Barcode %s already exists as item %d (%s)", barcode, existing[0], existing[1])
            return {"item_id": existing[0], "status": "duplicate"}

    cur.execute("""
        INSERT INTO item (name, barcode, brand, category, description,
                          media_type, media_title, media_creator, media_year,
                          media_isbn, media_cover_url, media_genre,
                          media_subtitle, media_publisher, media_pages,
                          media_format, media_language, media_publish_date)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING id
    """, (
        name,
        barcode,
        body.get("brand"),
        body.get("category"),
        body.get("description"),
        body.get("media_type"),
        body.get("media_title"),
        body.get("media_creator"),
        body.get("media_year"),
        body.get("media_isbn"),
        body.get("media_cover_url"),
        body.get("media_genre"),
        body.get("media_subtitle"),
        body.get("media_publisher"),
        body.get("media_pages"),
        body.get("media_format"),
        body.get("media_language"),
        body.get("media_publish_date"),
    ))
    item_id = cur.fetchone()[0]

    # Link Immich asset if provided
    immich_asset_id = body.get("immich_asset_id")
    if immich_asset_id:
        filename = f"immich-{immich_asset_id}"
        cur.execute("""
            INSERT INTO item_image (item_id, filename, immich_asset_id, is_primary, caption)
            VALUES (%s, %s, %s, true, 'Barcode scan')
        """, (item_id, filename, immich_asset_id))

    conn.commit()

    # Download cover image if URL provided
    cover_url = body.get("media_cover_url")
    if cover_url:
        download_cover_image(item_id, cover_url, conn)
    log.info("Pipeline ingested item %d: %s (barcode=%s)", item_id, name, barcode)
    return {"item_id": item_id, "status": "created"}
