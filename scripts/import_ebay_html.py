#!/usr/bin/env python3
"""Import eBay buy/sell history from an HTML data export into ebay_order.

Parses purchaseHistory.html and sellingHistory.html from the eBay data
export zip file, deduplicates against existing records, and inserts.

Usage:
    python scripts/import_ebay_html.py /path/to/ebayreports.zip
    python scripts/import_ebay_html.py /path/to/ebayreports.zip --dry-run
"""

import argparse
import html.parser
import json
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import psycopg2

from config.settings import settings

PURCHASE_COLS = 9  # date, item_id, title, price, qty, postage, total, currency, seller
SELLING_COLS = 8   # date, item_id, title, price, qty, postage, currency, buyer


class TableParser(html.parser.HTMLParser):
    """Extract all cell values from HTML tables."""

    def __init__(self):
        super().__init__()
        self.in_cell = False
        self.rows: list[list[str]] = []
        self.current_row: list[str] = []
        self.current_cell = ""

    def handle_starttag(self, tag, attrs):
        if tag == "tr":
            self.current_row = []
        elif tag in ("td", "th"):
            self.in_cell = True
            self.current_cell = ""

    def handle_endtag(self, tag):
        if tag in ("td", "th") and self.in_cell:
            self.in_cell = False
            self.current_row.append(self.current_cell.strip())
        elif tag == "tr":
            if self.current_row:
                self.rows.append(self.current_row)

    def handle_data(self, data):
        if self.in_cell:
            self.current_cell += data


def parse_date(date_str: str) -> str | None:
    """Parse 'Feb 09, 2024 02:35 PM' into ISO 8601."""
    try:
        dt = datetime.strptime(date_str, "%b %d, %Y %I:%M %p")
        return dt.replace(tzinfo=timezone.utc).isoformat()
    except ValueError:
        return None


def parse_html(zip_path: str, inner_path: str) -> list[list[str]]:
    """Read an HTML file from the zip and return table rows (excluding header)."""
    with zipfile.ZipFile(zip_path) as z:
        content = z.read(inner_path).decode("utf-8")
    parser = TableParser()
    parser.feed(content)
    return parser.rows


def extract_purchases(zip_path: str) -> list[dict]:
    """Parse purchase history HTML into order dicts."""
    rows = parse_html(zip_path, "ebayReports/reports/transactionreports/purchaseHistory.html")
    if len(rows) < 2:
        return []

    # The HTML has nested tables — all data rows contain the same concatenated cells.
    # Use the first data row and chunk by PURCHASE_COLS.
    cells = rows[1]
    orders = []
    for i in range(0, len(cells), PURCHASE_COLS):
        chunk = cells[i:i + PURCHASE_COLS]
        if len(chunk) < PURCHASE_COLS:
            break
        date_str, item_id, title, price, qty, _postage, total_price, currency, seller = chunk
        orders.append({
            "ebay_order_id": f"html-{item_id}",
            "ebay_item_id": item_id,
            "direction": "buy",
            "title": title,
            "quantity": int(qty) if qty else 1,
            "price": float(total_price) if total_price else None,
            "currency": currency or "GBP",
            "counterparty": seller,
            "order_date": parse_date(date_str),
            "ebay_url": f"https://www.ebay.co.uk/itm/{item_id}",
        })
    return orders


def extract_sales(zip_path: str) -> list[dict]:
    """Parse selling history HTML into order dicts."""
    rows = parse_html(zip_path, "ebayReports/reports/transactionreports/sellingHistory.html")
    if not rows:
        return []

    orders = []
    for row in rows[1:]:
        if len(row) < SELLING_COLS:
            continue
        date_str, item_id, title, price, qty, _postage, currency, buyer = row[:SELLING_COLS]
        orders.append({
            "ebay_order_id": f"html-{item_id}",
            "ebay_item_id": item_id,
            "direction": "sell",
            "title": title,
            "quantity": int(qty) if qty else 1,
            "price": float(price) if price else None,
            "currency": currency or "GBP",
            "counterparty": buyer,
            "order_date": parse_date(date_str),
            "ebay_url": f"https://www.ebay.co.uk/itm/{item_id}",
        })
    return orders


def main() -> None:
    parser = argparse.ArgumentParser(description="Import eBay HTML export into ebay_order")
    parser.add_argument("zip_path", help="Path to eBay reports zip file")
    parser.add_argument("--dry-run", action="store_true", help="Preview without writing to DB")
    args = parser.parse_args()

    if not Path(args.zip_path).exists():
        print(f"ERROR: {args.zip_path} not found", file=sys.stderr)
        sys.exit(1)

    print("Parsing purchase history...")
    purchases = extract_purchases(args.zip_path)
    print(f"  Found {len(purchases)} purchases")

    print("Parsing selling history...")
    sales = extract_sales(args.zip_path)
    print(f"  Found {len(sales)} sales")

    all_orders = purchases + sales
    if not all_orders:
        print("Nothing to import.")
        return

    conn = psycopg2.connect(settings.dsn)
    conn.autocommit = False
    cur = conn.cursor()

    try:
        # Load existing ebay_item_ids for cross-source dedup
        cur.execute("SELECT ebay_item_id, direction FROM ebay_order WHERE ebay_item_id IS NOT NULL")
        existing = {(row[0], row[1]) for row in cur.fetchall()}
        print(f"  {len(existing)} existing orders in DB")

        inserted = 0
        skipped_dedup = 0
        updated = 0

        for order in all_orders:
            key = (order["ebay_item_id"], order["direction"])
            if key in existing:
                # Already exists under a different order_id (API sync)
                if args.dry_run:
                    print(f"  [skip] {order['direction']}: {order['title']} (already in DB)")
                skipped_dedup += 1
                continue

            if args.dry_run:
                print(f"  [dry-run] {order['direction']}: {order['title']} - {order['currency']} {order['price']}")
                inserted += 1
                continue

            cur.execute("""
                INSERT INTO ebay_order (
                    ebay_order_id, direction, ebay_item_id, title, quantity,
                    price, currency, counterparty, order_date, status,
                    image_url, ebay_url, raw_json, synced_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, NULL, NULL, %s, %s, now())
                ON CONFLICT (ebay_order_id) DO UPDATE SET
                    title = EXCLUDED.title,
                    price = EXCLUDED.price,
                    counterparty = EXCLUDED.counterparty,
                    synced_at = now()
            """, (
                order["ebay_order_id"], order["direction"], order["ebay_item_id"],
                order["title"], order["quantity"], order["price"], order["currency"],
                order["counterparty"], order["order_date"], order["ebay_url"],
                json.dumps({"source": "html_export"}),
            ))

            # Track whether it was insert or update
            if cur.statusmessage == "INSERT 0 1":
                inserted += 1
            else:
                updated += 1

            # Add to existing set so duplicate item_ids within the file are caught
            existing.add(key)

        if not args.dry_run:
            conn.commit()

        print(f"\nResults:")
        print(f"  Inserted: {inserted}")
        print(f"  Updated:  {updated}")
        print(f"  Skipped (already in DB from API): {skipped_dedup}")
        print(f"  Total processed: {len(all_orders)}")

    finally:
        conn.close()


if __name__ == "__main__":
    main()
