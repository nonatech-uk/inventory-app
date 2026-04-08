"""Amazon order management — local DB storage + CSV upload."""

import csv
import io
import json
import logging
import re
from decimal import Decimal, InvalidOperation

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile
from psycopg2.extras import RealDictCursor

from src.api.deps import CurrentUser, get_conn, get_current_user
from src.api.models import (
    AmazonLinkCreate,
    AmazonLinkItem,
    AmazonOrderItem,
    AmazonOrderList,
    AmazonUploadResult,
)

log = logging.getLogger(__name__)
router = APIRouter()


# ── CSV parsing (ported from finance/scripts/amazon_load.py) ─────────────────


def _parse_price(price_str: str) -> Decimal | None:
    if not price_str:
        return None
    cleaned = re.sub(r"[£$€,\s]", "", price_str.strip())
    if not cleaned:
        return None
    try:
        return Decimal(cleaned)
    except InvalidOperation:
        return None


def _parse_csv(content: str) -> list[dict]:
    """Parse Amazon order history CSV into normalised dicts."""
    items: list[dict] = []
    reader = csv.DictReader(io.StringIO(content))
    for row in reader:
        order_id = row.get("order id", "").strip()
        order_date = row.get("order date", "").strip()
        if not order_id or not order_date:
            continue

        # Validate date
        try:
            from datetime import datetime
            parsed_date = datetime.strptime(order_date, "%Y-%m-%d").date()
        except ValueError:
            continue

        description = row.get("description", "").strip()
        if not description:
            continue

        try:
            quantity = int(row.get("quantity", "1").strip())
        except ValueError:
            quantity = 1

        unit_price = _parse_price(row.get("price", ""))
        asin = row.get("ASIN", "").strip() or None
        category = row.get("category", "").strip() or None
        is_sub = row.get("subscribe & save", "0").strip() == "1"
        order_url = row.get("order url", "").strip() or None
        item_url = row.get("item url", "").strip() or None
        raw_data = {k: v for k, v in row.items() if v}

        items.append({
            "order_id": order_id,
            "order_date": parsed_date,
            "asin": asin,
            "description": description,
            "quantity": quantity,
            "unit_price": unit_price,
            "category": category,
            "is_subscription": is_sub,
            "order_url": order_url,
            "item_url": item_url,
            "raw_data": raw_data,
        })

    return items


def _write_items(items: list[dict], conn) -> dict[str, int]:
    """Write parsed items to amazon_order_item. Idempotent."""
    cur = conn.cursor()
    inserted = 0
    for item in items:
        cur.execute("""
            INSERT INTO amazon_order_item (
                order_id, order_date, asin, description,
                quantity, unit_price, currency, category,
                order_url, item_url, is_subscription, raw_data
            ) VALUES (
                %s, %s, %s, %s,
                %s, %s, 'GBP', %s,
                %s, %s, %s, %s
            )
            ON CONFLICT (order_id, COALESCE(asin, ''), description) DO NOTHING
            RETURNING id
        """, (
            item["order_id"], item["order_date"], item["asin"],
            item["description"], item["quantity"], item["unit_price"],
            item["category"], item["order_url"], item["item_url"],
            item["is_subscription"], json.dumps(item["raw_data"]),
        ))
        if cur.fetchone():
            inserted += 1
    conn.commit()
    return {"inserted": inserted, "skipped": len(items) - inserted}


# ── Endpoints ────────────────────────────────────────────────────────────────


@router.post("/amazon/upload", response_model=AmazonUploadResult)
def upload_amazon_csv(
    file: UploadFile,
    conn=Depends(get_conn),
    _user: CurrentUser = Depends(get_current_user),
):
    """Upload an Amazon order history CSV for idempotent sync."""
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(400, "File must be a .csv")

    raw = file.file.read()
    # Handle BOM
    for enc in ("utf-8-sig", "utf-8", "latin-1"):
        try:
            content = raw.decode(enc)
            break
        except UnicodeDecodeError:
            continue
    else:
        raise HTTPException(400, "Could not decode CSV file")

    items = _parse_csv(content)
    if not items:
        raise HTTPException(400, "No valid order items found in CSV")

    result = _write_items(items, conn)
    return AmazonUploadResult(
        inserted=result["inserted"],
        skipped=result["skipped"],
        total=len(items),
    )


@router.get("/amazon/orders", response_model=AmazonOrderList)
def list_amazon_orders(
    q: str | None = Query(None),
    limit: int = Query(50, le=200),
    offset: int = Query(0, ge=0),
    conn=Depends(get_conn),
    _user: CurrentUser = Depends(get_current_user),
):
    """Browse Amazon order items with optional search."""
    cur = conn.cursor()

    where = ""
    params: list = []
    if q:
        where = "WHERE description ILIKE %s"
        params.append(f"%{q}%")

    cur.execute(f"SELECT count(*) FROM amazon_order_item {where}", params)
    total = cur.fetchone()[0]

    cur.execute(f"""
        SELECT id, order_id, order_date, asin, description, quantity,
               unit_price, currency, category, order_url, item_url,
               is_subscription, created_at
        FROM amazon_order_item
        {where}
        ORDER BY order_date DESC NULLS LAST, id DESC
        LIMIT %s OFFSET %s
    """, params + [limit, offset])

    items = [
        AmazonOrderItem(
            id=r[0], order_id=r[1], order_date=str(r[2]) if r[2] else None,
            asin=r[3], description=r[4], quantity=r[5],
            unit_price=float(r[6]) if r[6] else None, currency=r[7],
            category=r[8], order_url=r[9], item_url=r[10],
            is_subscription=r[11], created_at=str(r[12]),
        )
        for r in cur.fetchall()
    ]
    return AmazonOrderList(items=items, total=total)


@router.get("/amazon/search")
def search_amazon_orders(
    q: str | None = Query(None),
    asin: str | None = Query(None),
    limit: int = Query(20, le=100),
    conn=Depends(get_conn),
    _user: CurrentUser = Depends(get_current_user),
):
    """Search Amazon order history for item linking."""
    where_clauses = []
    params: list = []

    if q:
        where_clauses.append("description ILIKE %s")
        params.append(f"%{q}%")
    if asin:
        where_clauses.append("asin = %s")
        params.append(asin)

    if not where_clauses:
        raise HTTPException(400, "Provide q or asin parameter")

    where = " AND ".join(where_clauses)
    cur = conn.cursor()
    cur.execute(f"""
        SELECT order_id, order_date, asin, description, quantity,
               unit_price, currency, category
        FROM amazon_order_item
        WHERE {where}
        ORDER BY order_date DESC
        LIMIT %s
    """, params + [limit])

    return [
        {
            "order_id": r[0], "order_date": str(r[1]) if r[1] else None,
            "asin": r[2], "description": r[3], "quantity": r[4],
            "unit_price": float(r[5]) if r[5] else None,
            "currency": r[6], "category": r[7],
        }
        for r in cur.fetchall()
    ]


@router.post("/items/{item_id}/amazon", response_model=AmazonLinkItem, status_code=201)
def link_amazon_order(
    item_id: int,
    body: AmazonLinkCreate,
    conn=Depends(get_conn),
    _user: CurrentUser = Depends(get_current_user),
):
    cur = conn.cursor()
    cur.execute("SELECT id FROM item WHERE id = %s", (item_id,))
    if not cur.fetchone():
        raise HTTPException(404, "Item not found")

    cur.execute("""
        INSERT INTO item_amazon_link (
            item_id, amazon_order_id, amazon_asin,
            amazon_description, amazon_price, amazon_date
        ) VALUES (%s, %s, %s, %s, %s, %s)
        ON CONFLICT DO NOTHING
        RETURNING id, item_id, amazon_order_id, amazon_asin,
                  amazon_description, amazon_price, amazon_date, linked_at
    """, (
        item_id, body.amazon_order_id, body.amazon_asin,
        body.amazon_description, body.amazon_price, body.amazon_date,
    ))
    conn.commit()
    r = cur.fetchone()
    if not r:
        raise HTTPException(409, "Link already exists")
    return AmazonLinkItem(
        id=r[0], item_id=r[1], amazon_order_id=r[2], amazon_asin=r[3],
        amazon_description=r[4], amazon_price=float(r[5]) if r[5] else None,
        amazon_date=str(r[6]) if r[6] else None, linked_at=str(r[7]),
    )


@router.delete("/amazon-links/{link_id}", status_code=204)
def unlink_amazon_order(
    link_id: int,
    conn=Depends(get_conn),
    _user: CurrentUser = Depends(get_current_user),
):
    cur = conn.cursor()
    cur.execute("DELETE FROM item_amazon_link WHERE id = %s", (link_id,))
    conn.commit()
    if cur.rowcount == 0:
        raise HTTPException(404, "Amazon link not found")
