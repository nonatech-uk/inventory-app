"""Location hierarchy CRUD."""

from fastapi import APIRouter, Depends, HTTPException

from src.api.deps import CurrentUser, get_conn, get_current_user
from src.api.models import LocationCreate, LocationItem, LocationUpdate

router = APIRouter()


def _row_to_location(row) -> LocationItem:
    return LocationItem(
        id=row[0],
        name=row[1],
        type=row[2],
        parent_id=row[3],
        description=row[4],
        floor=row[5],
        item_count=row[6] if len(row) > 6 else 0,
    )


@router.get("/locations", response_model=list[LocationItem])
def list_locations(
    conn=Depends(get_conn),
    _user: CurrentUser = Depends(get_current_user),
):
    """Return all locations as a flat list with item counts."""
    cur = conn.cursor()
    cur.execute("""
        SELECT l.id, l.name, l.type, l.parent_id, l.description, l.floor,
               COUNT(i.id)::int AS item_count
        FROM location l
        LEFT JOIN item i ON i.location_id = l.id
        GROUP BY l.id
        ORDER BY l.name
    """)
    return [_row_to_location(r) for r in cur.fetchall()]


@router.get("/locations/tree", response_model=list[LocationItem])
def get_location_tree(
    conn=Depends(get_conn),
    _user: CurrentUser = Depends(get_current_user),
):
    """Return locations as a nested tree."""
    cur = conn.cursor()
    cur.execute("""
        SELECT l.id, l.name, l.type, l.parent_id, l.description, l.floor,
               COUNT(i.id)::int AS item_count
        FROM location l
        LEFT JOIN item i ON i.location_id = l.id
        GROUP BY l.id
        ORDER BY l.name
    """)
    rows = cur.fetchall()
    all_locs = {r[0]: _row_to_location(r) for r in rows}

    roots: list[LocationItem] = []
    for loc in all_locs.values():
        if loc.parent_id and loc.parent_id in all_locs:
            all_locs[loc.parent_id].children.append(loc)
        else:
            roots.append(loc)
    return roots


@router.get("/locations/{location_id}", response_model=LocationItem)
def get_location(
    location_id: int,
    conn=Depends(get_conn),
    _user: CurrentUser = Depends(get_current_user),
):
    cur = conn.cursor()
    cur.execute("""
        SELECT l.id, l.name, l.type, l.parent_id, l.description, l.floor,
               COUNT(i.id)::int AS item_count
        FROM location l
        LEFT JOIN item i ON i.location_id = l.id
        WHERE l.id = %s
        GROUP BY l.id
    """, (location_id,))
    row = cur.fetchone()
    if not row:
        raise HTTPException(404, "Location not found")
    return _row_to_location(row)


@router.get("/locations/{location_id}/path")
def get_location_path(
    location_id: int,
    conn=Depends(get_conn),
    _user: CurrentUser = Depends(get_current_user),
):
    """Return the full path from root to this location."""
    cur = conn.cursor()
    cur.execute("""
        WITH RECURSIVE ancestors AS (
            SELECT id, name, parent_id, 1 AS depth
            FROM location WHERE id = %s
            UNION ALL
            SELECT l.id, l.name, l.parent_id, a.depth + 1
            FROM location l
            JOIN ancestors a ON l.id = a.parent_id
        )
        SELECT id, name FROM ancestors ORDER BY depth DESC
    """, (location_id,))
    return [{"id": r[0], "name": r[1]} for r in cur.fetchall()]


@router.post("/locations", response_model=LocationItem, status_code=201)
def create_location(
    body: LocationCreate,
    conn=Depends(get_conn),
    _user: CurrentUser = Depends(get_current_user),
):
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO location (name, type, parent_id, description, floor)
        VALUES (%s, %s, %s, %s, %s)
        RETURNING id, name, type, parent_id, description, floor
    """, (body.name, body.type, body.parent_id, body.description, body.floor))
    conn.commit()
    row = cur.fetchone()
    return _row_to_location((*row, 0))


@router.put("/locations/{location_id}", response_model=LocationItem)
def update_location(
    location_id: int,
    body: LocationUpdate,
    conn=Depends(get_conn),
    _user: CurrentUser = Depends(get_current_user),
):
    cur = conn.cursor()
    # Prevent circular parent references
    if body.parent_id is not None and body.parent_id == location_id:
        raise HTTPException(400, "Location cannot be its own parent")

    fields = []
    values = []
    for field_name in ("name", "type", "parent_id", "description", "floor"):
        val = getattr(body, field_name)
        if val is not None:
            fields.append(f"{field_name} = %s")
            values.append(val)

    if not fields:
        raise HTTPException(400, "No fields to update")

    fields.append("updated_at = now()")
    values.append(location_id)

    cur.execute(
        f"UPDATE location SET {', '.join(fields)} WHERE id = %s "
        f"RETURNING id, name, type, parent_id, description, floor",
        values,
    )
    conn.commit()
    row = cur.fetchone()
    if not row:
        raise HTTPException(404, "Location not found")
    return _row_to_location((*row, 0))


@router.delete("/locations/{location_id}", status_code=204)
def delete_location(
    location_id: int,
    conn=Depends(get_conn),
    _user: CurrentUser = Depends(get_current_user),
):
    cur = conn.cursor()
    cur.execute("DELETE FROM location WHERE id = %s", (location_id,))
    conn.commit()
    if cur.rowcount == 0:
        raise HTTPException(404, "Location not found")
