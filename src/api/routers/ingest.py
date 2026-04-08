"""Pipeline ingest endpoint — creates items from barcode scans."""

import logging

from fastapi import APIRouter, Depends, HTTPException, Request

from config.settings import settings
from src.api.deps import get_conn
from src.api.routers.images import download_cover_image

log = logging.getLogger(__name__)
router = APIRouter()


def _attach_immich_image(cur, conn, item_id: int, body: dict) -> None:
    """Attach an Immich asset image to an item if provided and not already linked."""
    immich_asset_id = body.get("immich_asset_id")
    if not immich_asset_id:
        return
    # Skip if already attached
    cur.execute(
        "SELECT 1 FROM item_image WHERE item_id = %s AND immich_asset_id = %s",
        (item_id, immich_asset_id),
    )
    if cur.fetchone():
        return
    barcode = body.get("barcode")
    caption = "Book cover" if body.get("media_type") == "book" and not barcode else "Barcode scan"
    is_primary = not bool(barcode)  # Cover photos are primary, barcode scans are not
    cur.execute("""
        INSERT INTO item_image (item_id, filename, immich_asset_id, is_primary, caption)
        VALUES (%s, %s, %s, %s, %s)
    """, (item_id, f"immich-{immich_asset_id}", immich_asset_id, is_primary, caption))
    conn.commit()
    log.info("Attached Immich asset %s to item %d", immich_asset_id, item_id)


def _fill_missing_fields(cur, conn, item_id: int, body: dict) -> None:
    """Fill in NULL fields on an existing item from new ingest data."""
    fillable = [
        "description", "media_subtitle", "media_creator", "media_isbn",
        "media_cover_url", "media_publisher", "media_pages", "media_format",
        "media_language", "media_publish_date", "media_genre",
    ]
    updates = []
    values = []
    for field in fillable:
        val = body.get(field)
        if val is not None:
            updates.append(f"{field} = COALESCE({field}, %s)")
            values.append(val)
    if not updates:
        return
    values.append(item_id)
    cur.execute(
        f"UPDATE item SET {', '.join(updates)} WHERE id = %s",
        values,
    )
    if cur.rowcount:
        conn.commit()
        log.info("Filled missing fields on item %d", item_id)


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
    existing_id = None
    if barcode:
        cur.execute("SELECT id, name FROM item WHERE barcode = %s", (barcode,))
        existing = cur.fetchone()
        if existing:
            existing_id = existing[0]
            log.info("Barcode %s already exists as item %d (%s)", barcode, existing_id, existing[1])

    # Check for duplicate book by title (fuzzy match via pg_trgm)
    if not existing_id and body.get("media_type") == "book" and body.get("media_title"):
        media_title = body["media_title"].strip()
        cur.execute(
            """SELECT id, name, media_title, similarity(LOWER(media_title), LOWER(%s)) AS sim
               FROM item WHERE media_type = 'book'
               AND similarity(LOWER(media_title), LOWER(%s)) > 0.4
               ORDER BY sim DESC LIMIT 1""",
            (media_title, media_title)
        )
        existing = cur.fetchone()
        if existing:
            existing_id = existing[0]
            log.info("Book '%s' fuzzy-matched item %d '%s' (sim=%.2f)", media_title, existing_id, existing[2], existing[3])

    if existing_id:
        _attach_immich_image(cur, conn, existing_id, body)
        _fill_missing_fields(cur, conn, existing_id, body)
        return {"item_id": existing_id, "status": "duplicate"}

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

    _attach_immich_image(cur, conn, item_id, body)
    conn.commit()

    # Download cover image if URL provided
    cover_url = body.get("media_cover_url")
    if cover_url:
        download_cover_image(item_id, cover_url, conn)
    log.info("Pipeline ingested item %d: %s (barcode=%s)", item_id, name, barcode)
    return {"item_id": item_id, "status": "created"}
