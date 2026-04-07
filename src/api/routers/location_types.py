"""Location type CRUD."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from src.api.deps import CurrentUser, get_conn, get_current_user

router = APIRouter()


class LocationType(BaseModel):
    id: int
    name: str
    sort_order: int


class LocationTypeCreate(BaseModel):
    name: str
    sort_order: int = 0


class LocationTypeUpdate(BaseModel):
    name: str | None = None
    sort_order: int | None = None


@router.get("/location-types", response_model=list[LocationType])
def list_location_types(
    conn=Depends(get_conn),
    _user: CurrentUser = Depends(get_current_user),
):
    cur = conn.cursor()
    cur.execute("SELECT id, name, sort_order FROM location_type ORDER BY sort_order, name")
    return [LocationType(id=r[0], name=r[1], sort_order=r[2]) for r in cur.fetchall()]


@router.post("/location-types", response_model=LocationType, status_code=201)
def create_location_type(
    body: LocationTypeCreate,
    conn=Depends(get_conn),
    _user: CurrentUser = Depends(get_current_user),
):
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO location_type (name, sort_order) VALUES (%s, %s) RETURNING id, name, sort_order",
        (body.name.strip().lower(), body.sort_order),
    )
    conn.commit()
    r = cur.fetchone()
    return LocationType(id=r[0], name=r[1], sort_order=r[2])


@router.put("/location-types/{type_id}", response_model=LocationType)
def update_location_type(
    type_id: int,
    body: LocationTypeUpdate,
    conn=Depends(get_conn),
    _user: CurrentUser = Depends(get_current_user),
):
    cur = conn.cursor()
    fields = []
    values = []
    if body.name is not None:
        fields.append("name = %s")
        values.append(body.name.strip().lower())
    if body.sort_order is not None:
        fields.append("sort_order = %s")
        values.append(body.sort_order)
    if not fields:
        raise HTTPException(400, "No fields to update")
    values.append(type_id)
    cur.execute(
        f"UPDATE location_type SET {', '.join(fields)} WHERE id = %s RETURNING id, name, sort_order",
        values,
    )
    conn.commit()
    r = cur.fetchone()
    if not r:
        raise HTTPException(404, "Location type not found")
    return LocationType(id=r[0], name=r[1], sort_order=r[2])


@router.delete("/location-types/{type_id}", status_code=204)
def delete_location_type(
    type_id: int,
    conn=Depends(get_conn),
    _user: CurrentUser = Depends(get_current_user),
):
    cur = conn.cursor()
    # Check if any locations use this type
    cur.execute(
        "SELECT lt.name, COUNT(l.id) FROM location_type lt LEFT JOIN location l ON l.type = lt.name WHERE lt.id = %s GROUP BY lt.name",
        (type_id,),
    )
    row = cur.fetchone()
    if not row:
        raise HTTPException(404, "Location type not found")
    if row[1] > 0:
        raise HTTPException(409, f"Cannot delete: {row[1]} location(s) use type '{row[0]}'")
    cur.execute("DELETE FROM location_type WHERE id = %s", (type_id,))
    conn.commit()
