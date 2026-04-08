#!/bin/bash
# One-time migration: copy amazon_order_item from finance DB to stuff DB.
# Both databases are on the same PostgreSQL host.
#
# Usage: bash scripts/migrate_amazon_from_finance.sh
#
# Requires: psql, access to both databases.

set -euo pipefail

DB_HOST="${DB_HOST:-192.168.128.9}"
DB_PORT="${DB_PORT:-5432}"
FINANCE_DB="finance"
FINANCE_USER="finance"
STUFF_DB="stuff"
STUFF_USER="stuff"

echo "=== Amazon Order Migration: finance → stuff ==="

# Count source rows
SRC_COUNT=$(psql -h "$DB_HOST" -p "$DB_PORT" -U "$FINANCE_USER" -d "$FINANCE_DB" -tAc \
    "SELECT count(*) FROM amazon_order_item")
echo "Source rows in finance.amazon_order_item: $SRC_COUNT"

if [ "$SRC_COUNT" -eq 0 ]; then
    echo "No rows to migrate."
    exit 0
fi

# Ensure target table exists (schema.sql should have been applied already)
DST_COUNT=$(psql -h "$DB_HOST" -p "$DB_PORT" -U "$STUFF_USER" -d "$STUFF_DB" -tAc \
    "SELECT count(*) FROM amazon_order_item" 2>/dev/null || echo "TABLE_MISSING")

if [ "$DST_COUNT" = "TABLE_MISSING" ]; then
    echo "ERROR: amazon_order_item table does not exist in stuff DB."
    echo "Deploy the updated schema.sql first."
    exit 1
fi

echo "Existing rows in stuff.amazon_order_item: $DST_COUNT"

# Export from finance and import to stuff via COPY pipe
echo "Copying data..."
psql -h "$DB_HOST" -p "$DB_PORT" -U "$FINANCE_USER" -d "$FINANCE_DB" -c \
    "COPY (SELECT order_id, order_date, asin, description, quantity, unit_price,
            currency, category, order_url, item_url, is_subscription, raw_data, created_at
     FROM amazon_order_item ORDER BY id) TO STDOUT WITH (FORMAT csv, HEADER)" \
| psql -h "$DB_HOST" -p "$DB_PORT" -U "$STUFF_USER" -d "$STUFF_DB" -c \
    "CREATE TEMP TABLE _import (LIKE amazon_order_item INCLUDING NOTHING);
     ALTER TABLE _import DROP COLUMN id;
     COPY _import (order_id, order_date, asin, description, quantity, unit_price,
                   currency, category, order_url, item_url, is_subscription, raw_data, created_at)
     FROM STDIN WITH (FORMAT csv, HEADER);
     INSERT INTO amazon_order_item (order_id, order_date, asin, description, quantity, unit_price,
                                    currency, category, order_url, item_url, is_subscription, raw_data, created_at)
     SELECT order_id, order_date, asin, description, quantity, unit_price,
            currency, category, order_url, item_url, is_subscription, raw_data, created_at
     FROM _import
     ON CONFLICT (order_id, COALESCE(asin, ''), description) DO NOTHING;
     DROP TABLE _import;"

# Verify
FINAL_COUNT=$(psql -h "$DB_HOST" -p "$DB_PORT" -U "$STUFF_USER" -d "$STUFF_DB" -tAc \
    "SELECT count(*) FROM amazon_order_item")
echo ""
echo "Migration complete."
echo "  Source (finance): $SRC_COUNT rows"
echo "  Target (stuff):   $FINAL_COUNT rows"
echo "=== Done ==="
