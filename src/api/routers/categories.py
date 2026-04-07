"""Item category CRUD."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from src.api.deps import CurrentUser, get_conn, get_current_user

router = APIRouter()


class Category(BaseModel):
    id: int
    name: str
    sort_order: int


class CategoryCreate(BaseModel):
    name: str
    sort_order: int = 0


class CategoryUpdate(BaseModel):
    name: str | None = None
    sort_order: int | None = None


@router.get("/categories", response_model=list[Category])
def list_categories(
    conn=Depends(get_conn),
    _user: CurrentUser = Depends(get_current_user),
):
    cur = conn.cursor()
    cur.execute("SELECT id, name, sort_order FROM item_category ORDER BY sort_order, name")
    return [Category(id=r[0], name=r[1], sort_order=r[2]) for r in cur.fetchall()]


@router.post("/categories", response_model=Category, status_code=201)
def create_category(
    body: CategoryCreate,
    conn=Depends(get_conn),
    _user: CurrentUser = Depends(get_current_user),
):
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO item_category (name, sort_order) VALUES (%s, %s) RETURNING id, name, sort_order",
        (body.name.strip(), body.sort_order),
    )
    conn.commit()
    r = cur.fetchone()
    return Category(id=r[0], name=r[1], sort_order=r[2])


@router.put("/categories/{cat_id}", response_model=Category)
def update_category(
    cat_id: int,
    body: CategoryUpdate,
    conn=Depends(get_conn),
    _user: CurrentUser = Depends(get_current_user),
):
    cur = conn.cursor()
    fields = []
    values = []
    if body.name is not None:
        fields.append("name = %s")
        values.append(body.name.strip())
    if body.sort_order is not None:
        fields.append("sort_order = %s")
        values.append(body.sort_order)
    if not fields:
        raise HTTPException(400, "No fields to update")
    values.append(cat_id)
    cur.execute(
        f"UPDATE item_category SET {', '.join(fields)} WHERE id = %s RETURNING id, name, sort_order",
        values,
    )
    conn.commit()
    r = cur.fetchone()
    if not r:
        raise HTTPException(404, "Category not found")
    return Category(id=r[0], name=r[1], sort_order=r[2])


@router.delete("/categories/{cat_id}", status_code=204)
def delete_category(
    cat_id: int,
    conn=Depends(get_conn),
    _user: CurrentUser = Depends(get_current_user),
):
    cur = conn.cursor()
    cur.execute(
        "SELECT c.name, COUNT(i.id) FROM item_category c LEFT JOIN item i ON i.category = c.name WHERE c.id = %s GROUP BY c.name",
        (cat_id,),
    )
    row = cur.fetchone()
    if not row:
        raise HTTPException(404, "Category not found")
    if row[1] > 0:
        raise HTTPException(409, f"Cannot delete: {row[1]} item(s) use category '{row[0]}'")
    cur.execute("DELETE FROM item_category WHERE id = %s", (cat_id,))
    conn.commit()
