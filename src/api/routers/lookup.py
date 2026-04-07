"""Barcode/ISBN lookup — proxies to OpenLibrary, Open Food Facts, TMDB."""

import logging

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query

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

    cover_id = (data.get("covers") or [None])[0]
    cover_url = f"https://covers.openlibrary.org/b/id/{cover_id}-L.jpg" if cover_id else None

    return {
        "source": "openlibrary",
        "title": data.get("title"),
        "creator": ", ".join(authors) if authors else None,
        "year": (data.get("publish_date") or "")[:4] or None,
        "isbn": isbn,
        "cover_url": cover_url,
        "publishers": data.get("publishers"),
        "pages": data.get("number_of_pages"),
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
