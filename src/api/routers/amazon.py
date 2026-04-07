"""Amazon order linking — cross-DB queries to finance."""

import logging

import psycopg2
from fastapi import APIRouter, Depends, HTTPException, Query

from config.settings import settings
from src.api.deps import CurrentUser, get_conn, get_current_user
from src.api.models import AmazonLinkCreate, AmazonLinkItem

log = logging.getLogger(__name__)
router = APIRouter()


def _finance_query(query: str, params: tuple = ()) -> list:
    """Execute a read-only query against the finance database."""
    dsn = settings.cross_dsn(
        settings.finance_db_name,
        settings.finance_db_user,
        settings.finance_db_password,
    )
    try:
        conn = psycopg2.connect(dsn)
        conn.autocommit = True
        cur = conn.cursor()
        cur.execute(query, params)
        rows = cur.fetchall()
        conn.close()
        return rows
    except Exception:
        log.exception("Failed to query finance database")
        return []


@router.get("/amazon/search")
def search_amazon_orders(
    q: str | None = Query(None),
    asin: str | None = Query(None),
    limit: int = Query(20, le=100),
    _user: CurrentUser = Depends(get_current_user),
):
    """Search Amazon order history in the finance database."""
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
    rows = _finance_query(f"""
        SELECT order_id, order_date, asin, description, quantity,
               unit_price, currency, category
        FROM amazon_order_item
        WHERE {where}
        ORDER BY order_date DESC
        LIMIT %s
    """, tuple(params + [limit]))

    return [
        {
            "order_id": r[0], "order_date": str(r[1]) if r[1] else None,
            "asin": r[2], "description": r[3], "quantity": r[4],
            "unit_price": float(r[5]) if r[5] else None,
            "currency": r[6], "category": r[7],
        }
        for r in rows
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
