#!/usr/bin/env python3
"""Sync eBay buy/sell history into the local ebay_order cache.

Purchases via Trading API (GetMyeBayBuying), sells via REST Fulfillment API.

Usage:
    python scripts/sync_ebay.py
    python scripts/sync_ebay.py --dry-run
    python scripts/sync_ebay.py --days-back=365
"""

import argparse
import base64
import json
import sys
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import httpx
import psycopg2

from config.settings import settings

HC_UUID = ""  # TODO: create healthcheck at hc.mees.st and paste UUID here
HC_BASE = "https://hc.mees.st/ping"

EBAY_NS = "urn:ebay:apis:eBLBaseComponents"
TRADING_URL = "https://api.ebay.com/ws/api.dll"
TOKEN_URL = "https://api.ebay.com/identity/v1/oauth2/token"


def ping_hc(suffix: str = ""):
    if not HC_UUID:
        return
    try:
        httpx.get(f"{HC_BASE}/{HC_UUID}{suffix}", timeout=5)
    except Exception:
        pass


def refresh_access_token() -> str:
    """Exchange refresh token for a short-lived access token."""
    credentials = base64.b64encode(
        f"{settings.ebay_client_id}:{settings.ebay_client_secret}".encode()
    ).decode()

    resp = httpx.post(
        TOKEN_URL,
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "Authorization": f"Basic {credentials}",
        },
        data={
            "grant_type": "refresh_token",
            "refresh_token": settings.ebay_refresh_token,
            "scope": "https://api.ebay.com/oauth/api_scope",
        },
        timeout=15,
    )
    if resp.status_code != 200:
        raise RuntimeError(f"Token refresh failed: {resp.status_code} {resp.text}")

    return resp.json()["access_token"]


def _xml_text(elem, tag: str) -> str | None:
    """Get text content of a namespaced child element."""
    child = elem.find(f"{{{EBAY_NS}}}{tag}")
    if child is not None and child.text:
        return child.text.strip()
    return None


def _xml_nested(elem, *tags: str) -> str | None:
    """Navigate nested namespaced elements and return text of the last one."""
    current = elem
    for tag in tags:
        current = current.find(f"{{{EBAY_NS}}}{tag}")
        if current is None:
            return None
    return current.text.strip() if current is not None and current.text else None


def sync_purchases(token: str, cursor, days_back: int, dry_run: bool) -> int:
    """Fetch purchase history via Trading API GetMyeBayBuying."""
    now = datetime.now(timezone.utc)
    start = now - timedelta(days=days_back)

    page = 1
    total_synced = 0

    with httpx.Client(timeout=30) as client:
        while True:
            xml_request = f"""<?xml version="1.0" encoding="utf-8"?>
<GetMyeBayBuyingRequest xmlns="urn:ebay:apis:eBLBaseComponents">
    <RequesterCredentials>
        <eBayAuthToken>{token}</eBayAuthToken>
    </RequesterCredentials>
    <WonList>
        <Sort>EndTime</Sort>
        <Pagination>
            <EntriesPerPage>200</EntriesPerPage>
            <PageNumber>{page}</PageNumber>
        </Pagination>
    </WonList>
    <DetailLevel>ReturnAll</DetailLevel>
</GetMyeBayBuyingRequest>"""

            resp = client.post(
                TRADING_URL,
                content=xml_request,
                headers={
                    "Content-Type": "text/xml",
                    "X-EBAY-API-SITEID": settings.ebay_site_id,
                    "X-EBAY-API-COMPATIBILITY-LEVEL": "1267",
                    "X-EBAY-API-CALL-NAME": "GetMyeBayBuying",
                    "X-EBAY-API-IAF-TOKEN": token,
                },
            )
            resp.raise_for_status()

            root = ET.fromstring(resp.text)
            ack = _xml_text(root, "Ack")
            if ack not in ("Success", "Warning"):
                errors = root.findall(f".//{{{EBAY_NS}}}Errors/{{{EBAY_NS}}}LongMessage")
                msg = "; ".join(e.text for e in errors if e.text) or "Unknown error"
                print(f"  Trading API error: {msg}")
                break

            won_list = root.find(f"{{{EBAY_NS}}}WonList")
            if won_list is None:
                break

            items = won_list.findall(f"{{{EBAY_NS}}}OrderTransactionArray/{{{EBAY_NS}}}OrderTransaction")
            if not items:
                # Try individual transactions
                items = won_list.findall(f"{{{EBAY_NS}}}OrderTransactionArray/{{{EBAY_NS}}}OrderTransaction")
                if not items:
                    break

            for ot in items:
                # Try order-level first, then transaction-level
                order = ot.find(f"{{{EBAY_NS}}}Order")
                txn = ot.find(f"{{{EBAY_NS}}}Transaction")

                order_id = None
                if order is not None:
                    order_id = _xml_text(order, "OrderID")
                if not order_id and txn is not None:
                    order_id = _xml_text(txn, "TransactionID")
                if not order_id:
                    continue

                item_elem = None
                if txn is not None:
                    item_elem = txn.find(f"{{{EBAY_NS}}}Item")

                item_id = _xml_text(item_elem, "ItemID") if item_elem is not None else None
                title = _xml_text(item_elem, "Title") if item_elem is not None else None

                if not title:
                    title = order_id

                # Price — try multiple locations in order of preference
                price = None
                price_elem = None
                if txn is not None:
                    price_elem = txn.find(f"{{{EBAY_NS}}}TotalTransactionPrice")
                if price_elem is None and txn is not None:
                    price_elem = txn.find(f"{{{EBAY_NS}}}TotalPrice")
                if price_elem is None and order is not None:
                    price_elem = order.find(f"{{{EBAY_NS}}}Total")
                if price_elem is None and txn is not None:
                    price_elem = txn.find(f"{{{EBAY_NS}}}TransactionPrice")
                if price_elem is not None and price_elem.text:
                    try:
                        price = float(price_elem.text)
                    except ValueError:
                        pass

                currency = "GBP"
                if price_elem is not None:
                    currency = price_elem.get("currencyID", "GBP")

                # Quantity
                quantity = 1
                qty_text = _xml_text(txn, "QuantityPurchased") if txn is not None else None
                if qty_text:
                    try:
                        quantity = int(qty_text)
                    except ValueError:
                        pass

                # Date
                order_date = None
                date_text = None
                if order is not None:
                    date_text = _xml_text(order, "CreatedTime")
                if not date_text and txn is not None:
                    date_text = _xml_text(txn, "CreatedDate")
                if date_text:
                    order_date = date_text

                # Filter by date range
                if order_date:
                    try:
                        dt = datetime.fromisoformat(order_date.replace("Z", "+00:00"))
                        if dt < start:
                            continue
                    except ValueError:
                        pass

                # Seller
                seller = _xml_nested(txn, "Item", "Seller", "UserID") if txn is not None else None

                # Status
                status = _xml_text(order, "OrderStatus") if order is not None else None

                # Image
                image_url = _xml_nested(item_elem, "PictureDetails", "GalleryURL") if item_elem is not None else None

                # eBay URL
                ebay_url = _xml_nested(item_elem, "ListingDetails", "ViewItemURL") if item_elem is not None else None
                if not ebay_url and item_id:
                    ebay_url = f"https://www.ebay.co.uk/itm/{item_id}"

                if dry_run:
                    print(f"  [dry-run] buy: {title} ({order_id}) £{price}")
                else:
                    cursor.execute("""
                        INSERT INTO ebay_order (
                            ebay_order_id, direction, ebay_item_id, title, quantity,
                            price, currency, counterparty, order_date, status,
                            image_url, ebay_url, raw_json, synced_at
                        ) VALUES (%s, 'buy', %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, now())
                        ON CONFLICT (ebay_order_id) DO UPDATE SET
                            title = EXCLUDED.title,
                            price = EXCLUDED.price,
                            status = EXCLUDED.status,
                            image_url = EXCLUDED.image_url,
                            synced_at = now()
                    """, (
                        order_id, item_id, title, quantity, price, currency,
                        seller, order_date, status, image_url, ebay_url,
                        json.dumps({"source": "trading_api"}),
                    ))

                total_synced += 1

            # Pagination
            total_pages_text = _xml_nested(won_list, "PaginationResult", "TotalNumberOfPages")
            total_pages = int(total_pages_text) if total_pages_text else 1
            if page >= total_pages:
                break
            page += 1

    return total_synced


def sync_sales(token: str, cursor, days_back: int, dry_run: bool) -> int:
    """Fetch sell history via Trading API GetMyeBaySelling (SoldList)."""
    now = datetime.now(timezone.utc)
    start = now - timedelta(days=days_back)

    page = 1
    total_synced = 0

    with httpx.Client(timeout=30) as client:
        while True:
            xml_request = f"""<?xml version="1.0" encoding="utf-8"?>
<GetMyeBaySellingRequest xmlns="urn:ebay:apis:eBLBaseComponents">
    <RequesterCredentials>
        <eBayAuthToken>{token}</eBayAuthToken>
    </RequesterCredentials>
    <SoldList>
        <Sort>EndTime</Sort>
        <Pagination>
            <EntriesPerPage>200</EntriesPerPage>
            <PageNumber>{page}</PageNumber>
        </Pagination>
    </SoldList>
    <DetailLevel>ReturnAll</DetailLevel>
</GetMyeBaySellingRequest>"""

            resp = client.post(
                TRADING_URL,
                content=xml_request,
                headers={
                    "Content-Type": "text/xml",
                    "X-EBAY-API-SITEID": settings.ebay_site_id,
                    "X-EBAY-API-COMPATIBILITY-LEVEL": "1267",
                    "X-EBAY-API-CALL-NAME": "GetMyeBaySelling",
                    "X-EBAY-API-IAF-TOKEN": token,
                },
            )
            resp.raise_for_status()

            root = ET.fromstring(resp.text)
            ack = _xml_text(root, "Ack")
            if ack not in ("Success", "Warning"):
                errors = root.findall(f".//{{{EBAY_NS}}}Errors/{{{EBAY_NS}}}LongMessage")
                msg = "; ".join(e.text for e in errors if e.text) or "Unknown error"
                print(f"  Trading API error (sells): {msg}")
                break

            sold_list = root.find(f"{{{EBAY_NS}}}SoldList")
            if sold_list is None:
                break

            items = sold_list.findall(f"{{{EBAY_NS}}}OrderTransactionArray/{{{EBAY_NS}}}OrderTransaction")
            if not items:
                break

            for ot in items:
                order = ot.find(f"{{{EBAY_NS}}}Order")
                txn = ot.find(f"{{{EBAY_NS}}}Transaction")

                order_id = None
                if order is not None:
                    order_id = _xml_text(order, "OrderID")
                if not order_id and txn is not None:
                    order_id = _xml_text(txn, "TransactionID")
                if not order_id:
                    continue

                item_elem = None
                if txn is not None:
                    item_elem = txn.find(f"{{{EBAY_NS}}}Item")

                item_id = _xml_text(item_elem, "ItemID") if item_elem is not None else None
                title = _xml_text(item_elem, "Title") if item_elem is not None else None
                if not title:
                    title = order_id

                # Price — try multiple locations in order of preference
                price = None
                price_elem = None
                if txn is not None:
                    price_elem = txn.find(f"{{{EBAY_NS}}}TotalTransactionPrice")
                if price_elem is None and txn is not None:
                    price_elem = txn.find(f"{{{EBAY_NS}}}TotalPrice")
                if price_elem is None and order is not None:
                    price_elem = order.find(f"{{{EBAY_NS}}}Total")
                if price_elem is None and txn is not None:
                    price_elem = txn.find(f"{{{EBAY_NS}}}TransactionPrice")
                if price_elem is not None and price_elem.text:
                    try:
                        price = float(price_elem.text)
                    except ValueError:
                        pass

                currency = "GBP"
                if price_elem is not None:
                    currency = price_elem.get("currencyID", "GBP")

                quantity = 1
                qty_text = _xml_text(txn, "QuantityPurchased") if txn is not None else None
                if qty_text:
                    try:
                        quantity = int(qty_text)
                    except ValueError:
                        pass

                # Date
                order_date = None
                date_text = None
                if order is not None:
                    date_text = _xml_text(order, "CreatedTime")
                if not date_text and txn is not None:
                    date_text = _xml_text(txn, "CreatedDate")
                if date_text:
                    order_date = date_text

                # Filter by date range
                if order_date:
                    try:
                        dt = datetime.fromisoformat(order_date.replace("Z", "+00:00"))
                        if dt < start:
                            continue
                    except ValueError:
                        pass

                # Buyer
                buyer = _xml_nested(txn, "Buyer", "UserID") if txn is not None else None

                # Status
                status = _xml_text(order, "OrderStatus") if order is not None else None

                # Image
                image_url = _xml_nested(item_elem, "PictureDetails", "GalleryURL") if item_elem is not None else None

                # eBay URL
                ebay_url = _xml_nested(item_elem, "ListingDetails", "ViewItemURL") if item_elem is not None else None
                if not ebay_url and item_id:
                    ebay_url = f"https://www.ebay.co.uk/itm/{item_id}"

                if dry_run:
                    print(f"  [dry-run] sell: {title} ({order_id}) £{price}")
                else:
                    cursor.execute("""
                        INSERT INTO ebay_order (
                            ebay_order_id, direction, ebay_item_id, title, quantity,
                            price, currency, counterparty, order_date, status,
                            image_url, ebay_url, raw_json, synced_at
                        ) VALUES (%s, 'sell', %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, now())
                        ON CONFLICT (ebay_order_id) DO UPDATE SET
                            title = EXCLUDED.title,
                            price = EXCLUDED.price,
                            status = EXCLUDED.status,
                            image_url = EXCLUDED.image_url,
                            synced_at = now()
                    """, (
                        order_id, item_id, title, quantity, price, currency,
                        buyer, order_date, status, image_url, ebay_url,
                        json.dumps({"source": "trading_api"}),
                    ))

                total_synced += 1

            # Pagination
            total_pages_text = _xml_nested(sold_list, "PaginationResult", "TotalNumberOfPages")
            total_pages = int(total_pages_text) if total_pages_text else 1
            if page >= total_pages:
                break
            page += 1

    return total_synced


def main() -> None:
    parser = argparse.ArgumentParser(description="Sync eBay orders")
    parser.add_argument("--dry-run", action="store_true", help="Show what would change without writing to DB")
    parser.add_argument("--days-back", type=int, default=30, help="How many days back to sync (default: 30)")
    args = parser.parse_args()

    if not settings.ebay_refresh_token:
        print("ERROR: EBAY_REFRESH_TOKEN not set in .env", file=sys.stderr)
        sys.exit(1)

    if not args.dry_run:
        ping_hc("/start")

    rc = 0
    try:
        print(f"Refreshing eBay access token...")
        token = refresh_access_token()
        print("Token refreshed")

        conn = psycopg2.connect(settings.dsn)
        conn.autocommit = False
        cur = conn.cursor()

        try:
            print(f"Syncing purchases (last {args.days_back} days)...")
            buy_count = sync_purchases(token, cur, args.days_back, args.dry_run)
            print(f"Purchases: {buy_count} synced")

            print(f"Syncing sales (last {args.days_back} days)...")
            sell_count = sync_sales(token, cur, args.days_back, args.dry_run)
            print(f"Sales: {sell_count} synced")

            if not args.dry_run:
                conn.commit()
                print(f"Total: {buy_count + sell_count} orders synced")
            else:
                print(f"[dry-run] Would sync {buy_count + sell_count} orders")
        finally:
            conn.close()

    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        rc = 1

    if not args.dry_run:
        ping_hc(f"/{rc}" if rc else "")

    sys.exit(rc)


if __name__ == "__main__":
    main()
