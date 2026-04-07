"""Paperless document linking."""

from fastapi import APIRouter, Depends, HTTPException

from src.api.deps import CurrentUser, get_conn, get_current_user
from src.api.models import DocumentCreate, DocumentItem

router = APIRouter()


@router.get("/items/{item_id}/documents", response_model=list[DocumentItem])
def list_documents(
    item_id: int,
    conn=Depends(get_conn),
    _user: CurrentUser = Depends(get_current_user),
):
    cur = conn.cursor()
    cur.execute("""
        SELECT id, item_id, paperless_document_id, document_type, description, created_at
        FROM item_document WHERE item_id = %s ORDER BY id
    """, (item_id,))
    return [
        DocumentItem(
            id=r[0], item_id=r[1], paperless_document_id=r[2],
            document_type=r[3], description=r[4], created_at=str(r[5]),
        )
        for r in cur.fetchall()
    ]


@router.post("/items/{item_id}/documents", response_model=DocumentItem, status_code=201)
def link_document(
    item_id: int,
    body: DocumentCreate,
    conn=Depends(get_conn),
    _user: CurrentUser = Depends(get_current_user),
):
    cur = conn.cursor()
    cur.execute("SELECT id FROM item WHERE id = %s", (item_id,))
    if not cur.fetchone():
        raise HTTPException(404, "Item not found")

    cur.execute("""
        INSERT INTO item_document (item_id, paperless_document_id, document_type, description)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (item_id, paperless_document_id) DO UPDATE SET
            document_type = EXCLUDED.document_type,
            description = EXCLUDED.description
        RETURNING id, item_id, paperless_document_id, document_type, description, created_at
    """, (item_id, body.paperless_document_id, body.document_type, body.description))
    conn.commit()
    r = cur.fetchone()
    return DocumentItem(
        id=r[0], item_id=r[1], paperless_document_id=r[2],
        document_type=r[3], description=r[4], created_at=str(r[5]),
    )


@router.delete("/documents/{document_id}", status_code=204)
def unlink_document(
    document_id: int,
    conn=Depends(get_conn),
    _user: CurrentUser = Depends(get_current_user),
):
    cur = conn.cursor()
    cur.execute("DELETE FROM item_document WHERE id = %s", (document_id,))
    conn.commit()
    if cur.rowcount == 0:
        raise HTTPException(404, "Document link not found")
