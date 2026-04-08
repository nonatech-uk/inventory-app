"""Item image upload, Immich attach, cover download, and serving."""

import hashlib
import io
import logging
import uuid
from pathlib import Path

import httpx
from fastapi import APIRouter, Depends, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel

from config.settings import settings

log = logging.getLogger(__name__)
from src.api.deps import CurrentUser, get_conn, get_current_user

router = APIRouter()

IMAGES_DIR = Path(settings.image_storage_path)
THUMB_DIR = IMAGES_DIR / "thumbs"


def _ensure_dirs():
    IMAGES_DIR.mkdir(parents=True, exist_ok=True)


def download_cover_image(item_id: int, url: str, conn) -> bool:
    """Download an image from a URL and attach it to an item. Returns True on success."""
    _ensure_dirs()
    try:
        with httpx.Client(timeout=15, follow_redirects=True) as client:
            resp = client.get(url)
            if resp.status_code != 200:
                return False
            content = resp.content
            if len(content) < 1000:  # too small, probably an error page
                return False
    except Exception:
        log.exception("Failed to download cover from %s", url)
        return False

    content_type = resp.headers.get("content-type", "")
    ext = ".jpg"
    if "png" in content_type:
        ext = ".png"
    elif "webp" in content_type:
        ext = ".webp"

    filename = f"{uuid.uuid4().hex}{ext}"
    (IMAGES_DIR / filename).write_bytes(content)

    cur = conn.cursor()
    cur.execute("""
        INSERT INTO item_image (item_id, filename, is_primary, caption)
        VALUES (%s, %s, true, 'Cover')
    """, (item_id, filename))
    conn.commit()
    log.info("Downloaded cover for item %d: %s", item_id, filename)
    return True
    THUMB_DIR.mkdir(parents=True, exist_ok=True)


@router.post("/items/{item_id}/images", status_code=201)
def upload_image(
    item_id: int,
    file: UploadFile,
    is_primary: bool = False,
    caption: str | None = None,
    conn=Depends(get_conn),
    _user: CurrentUser = Depends(get_current_user),
):
    _ensure_dirs()
    cur = conn.cursor()

    # Verify item exists
    cur.execute("SELECT id FROM item WHERE id = %s", (item_id,))
    if not cur.fetchone():
        raise HTTPException(404, "Item not found")

    ext = Path(file.filename or "image.jpg").suffix.lower()
    filename = f"{uuid.uuid4().hex}{ext}"
    file_path = IMAGES_DIR / filename
    content = file.file.read()
    file_path.write_bytes(content)

    if is_primary:
        cur.execute(
            "UPDATE item_image SET is_primary = false WHERE item_id = %s",
            (item_id,),
        )

    cur.execute("""
        INSERT INTO item_image (item_id, filename, is_primary, caption)
        VALUES (%s, %s, %s, %s)
        RETURNING id, item_id, filename, immich_asset_id, is_primary, caption, created_at
    """, (item_id, filename, is_primary, caption))
    conn.commit()
    row = cur.fetchone()
    return {
        "id": row[0], "item_id": row[1], "filename": row[2],
        "immich_asset_id": row[3], "is_primary": row[4],
        "caption": row[5], "created_at": str(row[6]),
    }


@router.post("/items/{item_id}/images/immich", status_code=201)
def attach_immich_image(
    item_id: int,
    immich_asset_id: str,
    is_primary: bool = False,
    caption: str | None = None,
    conn=Depends(get_conn),
    _user: CurrentUser = Depends(get_current_user),
):
    cur = conn.cursor()
    cur.execute("SELECT id FROM item WHERE id = %s", (item_id,))
    if not cur.fetchone():
        raise HTTPException(404, "Item not found")

    # Use asset ID as filename placeholder
    filename = f"immich-{immich_asset_id}"

    if is_primary:
        cur.execute(
            "UPDATE item_image SET is_primary = false WHERE item_id = %s",
            (item_id,),
        )

    cur.execute("""
        INSERT INTO item_image (item_id, filename, immich_asset_id, is_primary, caption)
        VALUES (%s, %s, %s, %s, %s)
        RETURNING id, item_id, filename, immich_asset_id, is_primary, caption, created_at
    """, (item_id, filename, immich_asset_id, is_primary, caption))
    conn.commit()
    row = cur.fetchone()
    return {
        "id": row[0], "item_id": row[1], "filename": row[2],
        "immich_asset_id": row[3], "is_primary": row[4],
        "caption": row[5], "created_at": str(row[6]),
    }


@router.get("/images/{filename}")
def serve_image(filename: str):
    # Proxy Immich asset thumbnails
    if filename.startswith("immich-"):
        asset_id = filename.removeprefix("immich-")
        return _proxy_immich_thumbnail(asset_id)

    file_path = IMAGES_DIR / filename
    if not file_path.is_file():
        raise HTTPException(404, "Image not found")
    return FileResponse(
        file_path,
        headers={"Cache-Control": "public, max-age=31536000, immutable"},
    )


def _proxy_immich_thumbnail(asset_id: str):
    """Fetch a thumbnail from Immich and return it.

    TODO: Immich strips EXIF from thumbnails and doesn't apply rotation
    for HEIC files. Needs investigation to map Immich orientation metadata
    to the correct rotation for thumbnails.
    """
    from fastapi.responses import Response

    try:
        with httpx.Client(timeout=10) as client:
            resp = client.get(
                f"{settings.immich_url}/api/assets/{asset_id}/thumbnail",
                headers={"x-api-key": settings.immich_api_key},
                params={"size": "preview"},
            )
        if resp.status_code != 200:
            raise HTTPException(404, "Immich asset not found")
        return Response(
            content=resp.content,
            media_type=resp.headers.get("content-type", "image/jpeg"),
            headers={"Cache-Control": "public, max-age=86400"},
        )
    except httpx.HTTPError:
        raise HTTPException(502, "Failed to fetch from Immich")


@router.get("/images/{filename}/thumb")
def serve_thumbnail(filename: str):
    if filename.startswith("immich-"):
        asset_id = filename.removeprefix("immich-")
        return _proxy_immich_thumbnail(asset_id)

    _ensure_dirs()
    thumb_path = THUMB_DIR / filename
    if not thumb_path.is_file():
        original = IMAGES_DIR / filename
        if not original.is_file():
            raise HTTPException(404, "Image not found")
        try:
            from PIL import Image
            img = Image.open(original)
            img.thumbnail((300, 300))
            img.save(thumb_path, quality=80)
        except Exception:
            return FileResponse(original)

    return FileResponse(
        thumb_path,
        headers={"Cache-Control": "public, max-age=31536000, immutable"},
    )


@router.delete("/images/{image_id}", status_code=204)
def delete_image(
    image_id: int,
    conn=Depends(get_conn),
    _user: CurrentUser = Depends(get_current_user),
):
    cur = conn.cursor()
    cur.execute(
        "SELECT filename, immich_asset_id FROM item_image WHERE id = %s",
        (image_id,),
    )
    row = cur.fetchone()
    if not row:
        raise HTTPException(404, "Image not found")

    # Delete file if it's a local upload (not Immich)
    if not row[1]:
        file_path = IMAGES_DIR / row[0]
        if file_path.is_file():
            file_path.unlink()
        thumb_path = THUMB_DIR / row[0]
        if thumb_path.is_file():
            thumb_path.unlink()

    cur.execute("DELETE FROM item_image WHERE id = %s", (image_id,))
    conn.commit()
