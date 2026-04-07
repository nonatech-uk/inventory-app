"""Barcode/ISBN lookup — proxies to OpenLibrary, Open Food Facts, TMDB."""

import io
import logging

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile
from PIL import Image
from pyzbar.pyzbar import decode as pyzbar_decode

from config.settings import settings
from src.api.deps import CurrentUser, get_current_user

log = logging.getLogger(__name__)
router = APIRouter()

_HTTP_TIMEOUT = 10.0


@router.get("/lookup/isbn/{isbn}")
def lookup_isbn(
    isbn: str,
    _user: CurrentUser = Depends(get_current_user),
):
    """Look up a book by ISBN via OpenLibrary."""
    with httpx.Client(timeout=_HTTP_TIMEOUT) as client:
        resp = client.get(
            f"https://openlibrary.org/isbn/{isbn}.json",
            follow_redirects=True,
        )
    if resp.status_code == 404:
        raise HTTPException(404, "ISBN not found")
    resp.raise_for_status()
    data = resp.json()

    # Resolve author names
    authors = []
    for author_ref in data.get("authors", []):
        key = author_ref.get("key", "")
        if key:
            with httpx.Client(timeout=_HTTP_TIMEOUT) as client:
                a_resp = client.get(
                    f"https://openlibrary.org{key}.json",
                    follow_redirects=True,
                )
            if a_resp.status_code == 200:
                authors.append(a_resp.json().get("name", ""))

    # Extract subjects from edition first
    subjects = data.get("subjects", [])

    # Fetch work-level description
    description = None
    works = data.get("works", [])
    if works:
        work_key = works[0].get("key", "")
        if work_key:
            with httpx.Client(timeout=_HTTP_TIMEOUT) as client:
                w_resp = client.get(
                    f"https://openlibrary.org{work_key}.json",
                    follow_redirects=True,
                )
            if w_resp.status_code == 200:
                w_data = w_resp.json()
                desc = w_data.get("description", "")
                if isinstance(desc, dict):
                    desc = desc.get("value", "")
                description = desc or None
                # Prefer work-level subjects if edition has none
                if not subjects:
                    subjects = w_data.get("subjects", [])

    cover_id = (data.get("covers") or [None])[0]
    cover_url = f"https://covers.openlibrary.org/b/id/{cover_id}-L.jpg" if cover_id else None

    # Parse publish_date to ISO date where possible
    publish_date_raw = data.get("publish_date", "")
    publish_date = None
    if publish_date_raw:
        from datetime import datetime as _dt
        for fmt in ("%B %d, %Y", "%Y-%m-%d", "%Y"):
            try:
                publish_date = _dt.strptime(publish_date_raw, fmt).date().isoformat()
                break
            except ValueError:
                continue

    # Resolve language codes
    languages = []
    for lang_ref in data.get("languages", []):
        key = lang_ref.get("key", "")
        code = key.rsplit("/", 1)[-1] if key else ""
        lang_map = {"eng": "English", "fre": "French", "ger": "German", "spa": "Spanish", "ita": "Italian"}
        languages.append(lang_map.get(code, code))

    return {
        "source": "openlibrary",
        "title": data.get("title"),
        "subtitle": data.get("subtitle"),
        "description": description,
        "creator": ", ".join(authors) if authors else None,
        "year": (publish_date_raw)[:4] or None,
        "isbn": isbn,
        "cover_url": cover_url,
        "publisher": ", ".join(data.get("publishers", [])) or None,
        "pages": data.get("number_of_pages"),
        "physical_format": data.get("physical_format"),
        "language": ", ".join(languages) if languages else None,
        "publish_date": publish_date,
        "subjects": subjects,
    }


@router.get("/lookup/barcode/{barcode}")
def lookup_barcode(
    barcode: str,
    _user: CurrentUser = Depends(get_current_user),
):
    """Look up a product by barcode via Open Food Facts."""
    with httpx.Client(timeout=_HTTP_TIMEOUT) as client:
        resp = client.get(
            f"https://world.openfoodfacts.org/api/v2/product/{barcode}.json",
        )
    if resp.status_code == 404:
        raise HTTPException(404, "Barcode not found")
    resp.raise_for_status()
    data = resp.json()

    if data.get("status") != 1:
        raise HTTPException(404, "Product not found")

    product = data.get("product", {})
    return {
        "source": "openfoodfacts",
        "name": product.get("product_name"),
        "brand": product.get("brands"),
        "category": product.get("categories"),
        "barcode": barcode,
        "image_url": product.get("image_url"),
    }


@router.post("/lookup/decode-barcode")
def decode_barcode(
    file: UploadFile,
    _user: CurrentUser = Depends(get_current_user),
):
    """Decode a barcode from an uploaded image using pyzbar."""
    content = file.file.read()
    if not content:
        raise HTTPException(400, "Empty file")

    try:
        img = Image.open(io.BytesIO(content))
    except Exception:
        raise HTTPException(400, "Invalid image")

    # Upscale low-res images (e.g. 640x480 webcam)
    if img.width < 1000:
        scale = 2
        img = img.resize((img.width * scale, img.height * scale), Image.LANCZOS)

    # Convert to grayscale for better barcode detection
    gray = img.convert("L")

    # Increase contrast — helps with low-res webcams
    from PIL import ImageEnhance
    enhanced = ImageEnhance.Contrast(gray).enhance(2.0)
    sharpened = ImageEnhance.Sharpness(enhanced).enhance(2.0)

    # Try multiple orientations: original, flipped, enhanced, enhanced+flipped
    for attempt in [gray, gray.transpose(Image.FLIP_LEFT_RIGHT),
                    sharpened, sharpened.transpose(Image.FLIP_LEFT_RIGHT)]:
        results = pyzbar_decode(attempt)
        if results:
            barcode = results[0].data.decode("utf-8")
            barcode_type = results[0].type
            log.info("Decoded barcode from image: %s (%s)", barcode, barcode_type)
            return {"barcode": barcode, "type": barcode_type}

    raise HTTPException(404, "No barcode found in image")


@router.get("/lookup/movie")
def lookup_movie(
    q: str = Query(..., min_length=1),
    _user: CurrentUser = Depends(get_current_user),
):
    """Search for a movie/TV show via TMDB."""
    if not settings.tmdb_api_key:
        raise HTTPException(501, "TMDB API key not configured")

    with httpx.Client(timeout=_HTTP_TIMEOUT) as client:
        resp = client.get(
            "https://api.themoviedb.org/3/search/multi",
            params={"api_key": settings.tmdb_api_key, "query": q},
        )
    resp.raise_for_status()
    results = resp.json().get("results", [])[:10]

    return [
        {
            "source": "tmdb",
            "title": r.get("title") or r.get("name"),
            "year": (r.get("release_date") or r.get("first_air_date") or "")[:4] or None,
            "media_type": r.get("media_type"),
            "cover_url": f"https://image.tmdb.org/t/p/w300{r['poster_path']}" if r.get("poster_path") else None,
            "overview": r.get("overview"),
            "tmdb_id": r.get("id"),
        }
        for r in results
    ]
