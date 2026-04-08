"""eBay order linking and marketplace compliance endpoints."""

import hashlib
import logging

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import JSONResponse, RedirectResponse

from config.settings import settings
from src.api.deps import CurrentUser, get_conn, get_current_user
from src.api.models import EbayLinkCreate, EbayLinkItem, EbayOrder

log = logging.getLogger(__name__)
router = APIRouter()

EBAY_AUTH_URL = "https://auth.ebay.com/oauth2/authorize"
EBAY_TOKEN_URL = "https://api.ebay.com/identity/v1/oauth2/token"
EBAY_SCOPES = "https://api.ebay.com/oauth/api_scope"


# --- Search & Link (authenticated, like Amazon) ---


@router.get("/ebay/search", response_model=list[EbayOrder])
def search_ebay_orders(
    q: str | None = Query(None),
    direction: str | None = Query(None),
    limit: int = Query(20, le=100),
    conn=Depends(get_conn),
    _user: CurrentUser = Depends(get_current_user),
):
    """Search cached eBay orders."""
    where_clauses = []
    params: list = []

    if q:
        where_clauses.append("to_tsvector('english', title) @@ plainto_tsquery('english', %s)")
        params.append(q)
    if direction:
        where_clauses.append("direction = %s")
        params.append(direction)

    if not where_clauses:
        raise HTTPException(400, "Provide q or direction parameter")

    where = " AND ".join(where_clauses)
    cur = conn.cursor()
    cur.execute(f"""
        SELECT ebay_order_id, direction, ebay_item_id, title, quantity,
               price, currency, counterparty, order_date, status,
               image_url, ebay_url
        FROM ebay_order
        WHERE {where}
        ORDER BY order_date DESC
        LIMIT %s
    """, tuple(params + [limit]))

    return [
        EbayOrder(
            ebay_order_id=r[0], direction=r[1], ebay_item_id=r[2],
            title=r[3], quantity=r[4],
            price=float(r[5]) if r[5] else None, currency=r[6],
            counterparty=r[7],
            order_date=str(r[8]) if r[8] else None, status=r[9],
            image_url=r[10], ebay_url=r[11],
        )
        for r in cur.fetchall()
    ]


@router.post("/items/{item_id}/ebay", response_model=EbayLinkItem, status_code=201)
def link_ebay_order(
    item_id: int,
    body: EbayLinkCreate,
    conn=Depends(get_conn),
    _user: CurrentUser = Depends(get_current_user),
):
    cur = conn.cursor()
    cur.execute("SELECT id FROM item WHERE id = %s", (item_id,))
    if not cur.fetchone():
        raise HTTPException(404, "Item not found")

    cur.execute("""
        INSERT INTO item_ebay_link (
            item_id, ebay_order_id, ebay_item_id,
            ebay_title, ebay_price, ebay_date, direction
        ) VALUES (%s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT DO NOTHING
        RETURNING id, item_id, ebay_order_id, ebay_item_id,
                  ebay_title, ebay_price, ebay_date, direction, linked_at
    """, (
        item_id, body.ebay_order_id, body.ebay_item_id,
        body.ebay_title, body.ebay_price, body.ebay_date, body.direction,
    ))
    conn.commit()
    r = cur.fetchone()
    if not r:
        raise HTTPException(409, "Link already exists")
    return EbayLinkItem(
        id=r[0], item_id=r[1], ebay_order_id=r[2], ebay_item_id=r[3],
        ebay_title=r[4], ebay_price=float(r[5]) if r[5] else None,
        ebay_date=str(r[6]) if r[6] else None, direction=r[7],
        linked_at=str(r[8]),
    )


@router.delete("/ebay-links/{link_id}", status_code=204)
def unlink_ebay_order(
    link_id: int,
    conn=Depends(get_conn),
    _user: CurrentUser = Depends(get_current_user),
):
    cur = conn.cursor()
    cur.execute("DELETE FROM item_ebay_link WHERE id = %s", (link_id,))
    conn.commit()
    if cur.rowcount == 0:
        raise HTTPException(404, "eBay link not found")


# --- OAuth (one-time setup, no user auth — eBay redirects here) ---


@router.get("/ebay/oauth/start")
def ebay_oauth_start():
    """Redirect to eBay consent page to authorize the app."""
    if not settings.ebay_client_id or not settings.ebay_ru_name:
        raise HTTPException(503, "eBay not configured")
    url = (
        f"{EBAY_AUTH_URL}"
        f"?client_id={settings.ebay_client_id}"
        f"&response_type=code"
        f"&redirect_uri={settings.ebay_ru_name}"
        f"&scope={EBAY_SCOPES}"
    )
    return RedirectResponse(url)


@router.get("/ebay/oauth/callback")
def ebay_oauth_callback(code: str = Query(...)):
    """Exchange eBay auth code for tokens. Returns the refresh token to save to .env."""
    import base64

    credentials = base64.b64encode(
        f"{settings.ebay_client_id}:{settings.ebay_client_secret}".encode()
    ).decode()

    redirect_uri = settings.ebay_ru_name
    resp = httpx.post(
        EBAY_TOKEN_URL,
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "Authorization": f"Basic {credentials}",
        },
        data={
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": redirect_uri,
        },
        timeout=15,
    )
    if resp.status_code != 200:
        log.error("eBay token exchange failed: %s %s", resp.status_code, resp.text)
        raise HTTPException(502, f"eBay token exchange failed: {resp.status_code}")

    data = resp.json()
    return {
        "message": "Save the refresh_token to your .env file as EBAY_REFRESH_TOKEN",
        "refresh_token": data.get("refresh_token"),
        "access_token_expires_in": data.get("expires_in"),
        "refresh_token_expires_in": data.get("refresh_token_expires_in"),
    }


# --- Privacy Policy (eBay compliance) ---


@router.get("/ebay/privacy")
def ebay_privacy():
    """Minimal privacy policy for eBay app compliance."""
    html = """<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Privacy Policy — Stuff</title>
<style>body{font-family:system-ui,sans-serif;max-width:640px;margin:2rem auto;padding:0 1rem;line-height:1.6;color:#333}
h1{font-size:1.4rem}h2{font-size:1.1rem;margin-top:1.5rem}</style></head><body>
<h1>Privacy Policy</h1>
<p>Last updated: 8 April 2026</p>
<p>Stuff is a personal home inventory application. It is not a commercial service and is operated solely for private use by its owner.</p>
<h2>Data collected via eBay</h2>
<p>This application connects to the eBay API to retrieve the owner's personal purchase and sale history. Data retrieved includes order IDs, item titles, prices, dates, and listing images. This data is stored in a private database accessible only to the owner.</p>
<h2>No third-party sharing</h2>
<p>No data obtained from eBay is shared with any third party, sold, or used for advertising.</p>
<h2>Data retention</h2>
<p>eBay data is retained indefinitely for personal record-keeping. If eBay notifies us of an account deletion, we will remove associated data.</p>
<h2>Contact</h2>
<p>For questions, contact the application owner directly.</p>
</body></html>"""
    from fastapi.responses import HTMLResponse
    return HTMLResponse(html)


# --- Marketplace Account Deletion Notification (eBay compliance, no auth) ---


@router.get("/ebay/deletion")
def ebay_deletion_challenge(challenge_code: str = Query(...)):
    """Respond to eBay's endpoint validation challenge."""
    endpoint = f"https://stuff.mees.st/api/v1/ebay/deletion"
    token = settings.ebay_verification_token
    digest = hashlib.sha256(
        (challenge_code + token + endpoint).encode()
    ).hexdigest()
    return JSONResponse({"challengeResponse": digest})


@router.post("/ebay/deletion")
async def ebay_deletion_notification(request: Request):
    """Handle eBay marketplace account deletion/closure notification."""
    body = await request.json()
    log.info("eBay account deletion notification: %s", body)
    return JSONResponse(status_code=200, content={})
