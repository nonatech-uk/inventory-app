"""Item CRUD, search, and filtering."""

from fastapi import APIRouter, Depends, HTTPException, Query

from src.api.deps import CurrentUser, get_conn, get_current_user
from src.api.models import ItemCreate, ItemDetail, ItemList, ItemSummary, ItemUpdate

router = APIRouter()

_SUMMARY_COLS = """
    i.id, i.name, i.description, i.category, i.quantity,
    i.purchase_price, i.current_value, i.currency, i.brand, i.model,
    i.status, i.media_type, i.media_title, i.media_creator,
    i.location_id, l.name AS location_name, i.created_at
"""

_DETAIL_COLS = """
    i.id, i.name, i.description, i.location_id, l.name AS location_name,
    i.category, i.quantity, i.purchase_date, i.purchase_price,
    i.current_value, i.currency, i.brand, i.model, i.serial_number,
    i.barcode, i.notes, i.media_type, i.media_title, i.media_creator,
    i.media_year, i.media_isbn, i.media_cover_url, i.media_genre,
    i.is_insured, i.status, i.created_at, i.updated_at
"""


def _location_path(cur, location_id: int | None) -> str | None:
    if not location_id:
        return None
    cur.execute("""
        WITH RECURSIVE ancestors AS (
            SELECT id, name, parent_id, 1 AS depth
            FROM location WHERE id = %s
            UNION ALL
            SELECT l.id, l.name, l.parent_id, a.depth + 1
            FROM location l
            JOIN ancestors a ON l.id = a.parent_id
        )
        SELECT name FROM ancestors ORDER BY depth DESC
    """, (location_id,))
    parts = [r[0] for r in cur.fetchall()]
    return " > ".join(parts) if parts else None


def _primary_image(cur, item_id: int) -> str | None:
    cur.execute("""
        SELECT filename FROM item_image
        WHERE item_id = %s
        ORDER BY is_primary DESC, id ASC
        LIMIT 1
    """, (item_id,))
    row = cur.fetchone()
    return row[0] if row else None


def _row_to_summary(row, cur) -> ItemSummary:
    return ItemSummary(
        id=row[0], name=row[1], description=row[2], category=row[3],
        quantity=row[4], purchase_price=float(row[5]) if row[5] else None,
        current_value=float(row[6]) if row[6] else None, currency=row[7],
        brand=row[8], model=row[9], status=row[10],
        media_type=row[11], media_title=row[12], media_creator=row[13],
        location_id=row[14], location_name=row[15],
        location_path=_location_path(cur, row[14]),
        primary_image=_primary_image(cur, row[0]),
        created_at=str(row[16]),
    )


def _row_to_detail(row, cur) -> ItemDetail:
    item_id = row[0]
    location_id = row[3]

    # Fetch images
    cur.execute("""
        SELECT id, item_id, filename, immich_asset_id, is_primary, caption, created_at
        FROM item_image WHERE item_id = %s ORDER BY is_primary DESC, id
    """, (item_id,))
    images = [
        {"id": r[0], "item_id": r[1], "filename": r[2], "immich_asset_id": r[3],
         "is_primary": r[4], "caption": r[5], "created_at": str(r[6])}
        for r in cur.fetchall()
    ]

    # Fetch documents
    cur.execute("""
        SELECT id, item_id, paperless_document_id, document_type, description, created_at
        FROM item_document WHERE item_id = %s ORDER BY id
    """, (item_id,))
    documents = [
        {"id": r[0], "item_id": r[1], "paperless_document_id": r[2],
         "document_type": r[3], "description": r[4], "created_at": str(r[5])}
        for r in cur.fetchall()
    ]

    # Fetch amazon links
    cur.execute("""
        SELECT id, item_id, amazon_order_id, amazon_asin, amazon_description,
               amazon_price, amazon_date, linked_at
        FROM item_amazon_link WHERE item_id = %s ORDER BY id
    """, (item_id,))
    amazon_links = [
        {"id": r[0], "item_id": r[1], "amazon_order_id": r[2], "amazon_asin": r[3],
         "amazon_description": r[4], "amazon_price": float(r[5]) if r[5] else None,
         "amazon_date": str(r[6]) if r[6] else None, "linked_at": str(r[7])}
        for r in cur.fetchall()
    ]

    return ItemDetail(
        id=row[0], name=row[1], description=row[2],
        location_id=row[3], location_name=row[4],
        location_path=_location_path(cur, location_id),
        category=row[5], quantity=row[6],
        purchase_date=str(row[7]) if row[7] else None,
        purchase_price=float(row[8]) if row[8] else None,
        current_value=float(row[9]) if row[9] else None,
        currency=row[10], brand=row[11], model=row[12],
        serial_number=row[13], barcode=row[14], notes=row[15],
        media_type=row[16], media_title=row[17], media_creator=row[18],
        media_year=row[19], media_isbn=row[20], media_cover_url=row[21],
        media_genre=row[22], is_insured=row[23], status=row[24],
        created_at=str(row[25]), updated_at=str(row[26]),
        images=images,
        documents=documents,
        amazon_links=amazon_links,
    )


@router.get("/items", response_model=ItemList)
def list_items(
    location_id: int | None = Query(None),
    category: str | None = Query(None),
    status: str | None = Query(None),
    media_type: str | None = Query(None),
    q: str | None = Query(None),
    limit: int = Query(50, le=200),
    offset: int = Query(0, ge=0),
    conn=Depends(get_conn),
    _user: CurrentUser = Depends(get_current_user),
):
    cur = conn.cursor()
    where_clauses = []
    params: list = []

    if location_id is not None:
        # Include items in this location and all descendant locations
        where_clauses.append("""
            i.location_id IN (
                WITH RECURSIVE descendants AS (
                    SELECT id FROM location WHERE id = %s
                    UNION ALL
                    SELECT l.id FROM location l
                    JOIN descendants d ON l.parent_id = d.id
                )
                SELECT id FROM descendants
            )
        """)
        params.append(location_id)
    if category:
        where_clauses.append("i.category = %s")
        params.append(category)
    if status:
        where_clauses.append("i.status = %s")
        params.append(status)
    if media_type:
        where_clauses.append("i.media_type = %s")
        params.append(media_type)
    if q:
        where_clauses.append("i.search_vector @@ plainto_tsquery('english', %s)")
        params.append(q)

    where = "WHERE " + " AND ".join(where_clauses) if where_clauses else ""

    # Count
    cur.execute(f"SELECT COUNT(*) FROM item i {where}", params)
    total = cur.fetchone()[0]

    # Fetch
    cur.execute(f"""
        SELECT {_SUMMARY_COLS}
        FROM item i
        LEFT JOIN location l ON l.id = i.location_id
        {where}
        ORDER BY i.updated_at DESC
        LIMIT %s OFFSET %s
    """, params + [limit, offset])

    items = [_row_to_summary(r, cur) for r in cur.fetchall()]
    return ItemList(items=items, total=total, has_more=(offset + limit) < total)


@router.get("/items/{item_id}", response_model=ItemDetail)
def get_item(
    item_id: int,
    conn=Depends(get_conn),
    _user: CurrentUser = Depends(get_current_user),
):
    cur = conn.cursor()
    cur.execute(f"""
        SELECT {_DETAIL_COLS}
        FROM item i
        LEFT JOIN location l ON l.id = i.location_id
        WHERE i.id = %s
    """, (item_id,))
    row = cur.fetchone()
    if not row:
        raise HTTPException(404, "Item not found")
    return _row_to_detail(row, cur)


@router.post("/items", response_model=ItemDetail, status_code=201)
def create_item(
    body: ItemCreate,
    conn=Depends(get_conn),
    _user: CurrentUser = Depends(get_current_user),
):
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO item (
            name, description, location_id, category, quantity,
            purchase_date, purchase_price, current_value, currency,
            brand, model, serial_number, barcode, notes,
            media_type, media_title, media_creator, media_year,
            media_isbn, media_cover_url, media_genre,
            is_insured, status
        ) VALUES (
            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
            %s, %s, %s, %s, %s, %s, %s, %s, %s
        ) RETURNING id
    """, (
        body.name, body.description, body.location_id, body.category,
        body.quantity, body.purchase_date, body.purchase_price,
        body.current_value, body.currency, body.brand, body.model,
        body.serial_number, body.barcode, body.notes,
        body.media_type, body.media_title, body.media_creator,
        body.media_year, body.media_isbn, body.media_cover_url,
        body.media_genre, body.is_insured, body.status,
    ))
    conn.commit()
    item_id = cur.fetchone()[0]

    cur.execute(f"""
        SELECT {_DETAIL_COLS}
        FROM item i
        LEFT JOIN location l ON l.id = i.location_id
        WHERE i.id = %s
    """, (item_id,))
    return _row_to_detail(cur.fetchone(), cur)


@router.put("/items/{item_id}", response_model=ItemDetail)
def update_item(
    item_id: int,
    body: ItemUpdate,
    conn=Depends(get_conn),
    _user: CurrentUser = Depends(get_current_user),
):
    cur = conn.cursor()
    fields = []
    values = []
    for field_name in (
        "name", "description", "location_id", "category", "quantity",
        "purchase_date", "purchase_price", "current_value", "currency",
        "brand", "model", "serial_number", "barcode", "notes",
        "media_type", "media_title", "media_creator", "media_year",
        "media_isbn", "media_cover_url", "media_genre",
        "is_insured", "status",
    ):
        val = getattr(body, field_name)
        if val is not None:
            fields.append(f"{field_name} = %s")
            values.append(val)

    if not fields:
        raise HTTPException(400, "No fields to update")

    fields.append("updated_at = now()")
    values.append(item_id)

    cur.execute(
        f"UPDATE item SET {', '.join(fields)} WHERE id = %s RETURNING id",
        values,
    )
    conn.commit()
    if not cur.fetchone():
        raise HTTPException(404, "Item not found")

    cur.execute(f"""
        SELECT {_DETAIL_COLS}
        FROM item i
        LEFT JOIN location l ON l.id = i.location_id
        WHERE i.id = %s
    """, (item_id,))
    return _row_to_detail(cur.fetchone(), cur)


@router.delete("/items/{item_id}", status_code=204)
def delete_item(
    item_id: int,
    conn=Depends(get_conn),
    _user: CurrentUser = Depends(get_current_user),
):
    cur = conn.cursor()
    cur.execute("DELETE FROM item WHERE id = %s", (item_id,))
    conn.commit()
    if cur.rowcount == 0:
        raise HTTPException(404, "Item not found")
