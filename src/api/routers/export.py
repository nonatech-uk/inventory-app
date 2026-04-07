"""CSV export for insurance purposes."""

import csv
import io

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from src.api.deps import CurrentUser, get_conn, get_current_user

router = APIRouter()


@router.get("/export/csv")
def export_csv(
    conn=Depends(get_conn),
    _user: CurrentUser = Depends(get_current_user),
):
    cur = conn.cursor()
    cur.execute("""
        SELECT i.name, i.description, i.category, i.quantity,
               i.purchase_date, i.purchase_price, i.current_value, i.currency,
               i.brand, i.model, i.serial_number, i.barcode,
               i.status, i.is_insured, l.name AS location,
               i.media_type, i.media_title, i.media_creator
        FROM item i
        LEFT JOIN location l ON l.id = i.location_id
        ORDER BY i.name
    """)

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Name", "Description", "Category", "Quantity",
        "Purchase Date", "Purchase Price", "Current Value", "Currency",
        "Brand", "Model", "Serial Number", "Barcode",
        "Status", "Insured", "Location",
        "Media Type", "Media Title", "Media Creator",
    ])
    for row in cur.fetchall():
        writer.writerow([str(v) if v is not None else "" for v in row])

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=inventory.csv"},
    )
