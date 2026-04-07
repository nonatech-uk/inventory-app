"""Dashboard statistics."""

from fastapi import APIRouter, Depends

from src.api.deps import CurrentUser, get_conn, get_current_user

router = APIRouter()


@router.get("/stats/overview")
def get_overview(
    conn=Depends(get_conn),
    _user: CurrentUser = Depends(get_current_user),
):
    cur = conn.cursor()

    cur.execute("SELECT COUNT(*) FROM item")
    total_items = cur.fetchone()[0]

    cur.execute("SELECT COALESCE(SUM(current_value * quantity), 0) FROM item WHERE current_value IS NOT NULL")
    total_value = float(cur.fetchone()[0])

    cur.execute("SELECT COUNT(*) FROM location")
    total_locations = cur.fetchone()[0]

    cur.execute("SELECT status, COUNT(*) FROM item GROUP BY status ORDER BY COUNT(*) DESC")
    items_by_status = {r[0]: r[1] for r in cur.fetchall()}

    cur.execute("""
        SELECT COALESCE(category, 'Uncategorised'), COUNT(*)
        FROM item GROUP BY category ORDER BY COUNT(*) DESC
    """)
    items_by_category = {r[0]: r[1] for r in cur.fetchall()}

    return {
        "total_items": total_items,
        "total_value": total_value,
        "total_locations": total_locations,
        "items_by_status": items_by_status,
        "items_by_category": items_by_category,
    }


@router.get("/stats/by-location")
def stats_by_location(
    conn=Depends(get_conn),
    _user: CurrentUser = Depends(get_current_user),
):
    cur = conn.cursor()
    cur.execute("""
        SELECT l.name, COUNT(i.id)::int AS item_count,
               COALESCE(SUM(i.current_value * i.quantity), 0) AS total_value
        FROM location l
        LEFT JOIN item i ON i.location_id = l.id
        WHERE l.parent_id IS NULL
        GROUP BY l.id, l.name
        ORDER BY total_value DESC
    """)
    return [
        {"location": r[0], "item_count": r[1], "total_value": float(r[2])}
        for r in cur.fetchall()
    ]
