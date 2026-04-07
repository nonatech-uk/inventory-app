-- Home Inventory ("stuff") database schema

CREATE TABLE IF NOT EXISTS app_user (
    email TEXT PRIMARY KEY,
    display_name TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'admin'
);
INSERT INTO app_user (email, display_name, role)
VALUES ('stu@mees.st', 'Stu', 'admin')
ON CONFLICT DO NOTHING;

CREATE TABLE IF NOT EXISTS location_type (
    id SERIAL PRIMARY KEY,
    name TEXT UNIQUE NOT NULL,
    sort_order INTEGER NOT NULL DEFAULT 0
);
INSERT INTO location_type (name, sort_order) VALUES
    ('room', 1), ('cupboard', 2), ('drawer', 3), ('shelf', 4),
    ('box', 5), ('garage', 6), ('shed', 7), ('other', 8)
ON CONFLICT DO NOTHING;

CREATE TABLE IF NOT EXISTS item_category (
    id SERIAL PRIMARY KEY,
    name TEXT UNIQUE NOT NULL,
    sort_order INTEGER NOT NULL DEFAULT 0
);
INSERT INTO item_category (name, sort_order) VALUES
    ('Electronics', 1), ('Furniture', 2), ('Kitchen', 3), ('Tools', 4),
    ('Clothing', 5), ('Media', 6), ('Garden', 7), ('Sport', 8), ('Other', 9)
ON CONFLICT DO NOTHING;

CREATE TABLE IF NOT EXISTS location (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    type TEXT NOT NULL DEFAULT 'room',
    parent_id INTEGER REFERENCES location(id) ON DELETE SET NULL,
    description TEXT,
    floor TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_location_parent ON location(parent_id);

CREATE TABLE IF NOT EXISTS item (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    location_id INTEGER REFERENCES location(id) ON DELETE SET NULL,
    category TEXT,
    quantity INTEGER NOT NULL DEFAULT 1,
    purchase_date DATE,
    purchase_price NUMERIC(10,2),
    current_value NUMERIC(10,2),
    currency TEXT NOT NULL DEFAULT 'GBP',
    brand TEXT,
    model TEXT,
    serial_number TEXT,
    barcode TEXT,
    notes TEXT,
    media_type TEXT,
    media_title TEXT,
    media_creator TEXT,
    media_year INTEGER,
    media_isbn TEXT,
    media_cover_url TEXT,
    media_genre TEXT,
    is_insured BOOLEAN NOT NULL DEFAULT false,
    status TEXT NOT NULL DEFAULT 'owned',
    search_vector TSVECTOR,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_item_location ON item(location_id);
CREATE INDEX IF NOT EXISTS idx_item_category ON item(category);
CREATE INDEX IF NOT EXISTS idx_item_barcode ON item(barcode);
CREATE INDEX IF NOT EXISTS idx_item_status ON item(status);
CREATE INDEX IF NOT EXISTS idx_item_search ON item USING GIN(search_vector);

CREATE OR REPLACE FUNCTION item_search_update() RETURNS trigger AS $$
BEGIN
    NEW.search_vector := to_tsvector('english',
        coalesce(NEW.name, '') || ' ' ||
        coalesce(NEW.description, '') || ' ' ||
        coalesce(NEW.brand, '') || ' ' ||
        coalesce(NEW.model, '') || ' ' ||
        coalesce(NEW.serial_number, '') || ' ' ||
        coalesce(NEW.notes, '') || ' ' ||
        coalesce(NEW.media_title, '') || ' ' ||
        coalesce(NEW.media_creator, '')
    );
    RETURN NEW;
END $$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_item_search ON item;
CREATE TRIGGER trg_item_search BEFORE INSERT OR UPDATE ON item
FOR EACH ROW EXECUTE FUNCTION item_search_update();

CREATE TABLE IF NOT EXISTS item_image (
    id SERIAL PRIMARY KEY,
    item_id INTEGER NOT NULL REFERENCES item(id) ON DELETE CASCADE,
    filename TEXT NOT NULL,
    immich_asset_id TEXT,
    is_primary BOOLEAN NOT NULL DEFAULT false,
    caption TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_item_image_item ON item_image(item_id);

CREATE TABLE IF NOT EXISTS item_document (
    id SERIAL PRIMARY KEY,
    item_id INTEGER NOT NULL REFERENCES item(id) ON DELETE CASCADE,
    paperless_document_id INTEGER NOT NULL,
    document_type TEXT NOT NULL DEFAULT 'receipt',
    description TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(item_id, paperless_document_id)
);
CREATE INDEX IF NOT EXISTS idx_item_document_item ON item_document(item_id);

CREATE TABLE IF NOT EXISTS item_amazon_link (
    id SERIAL PRIMARY KEY,
    item_id INTEGER NOT NULL REFERENCES item(id) ON DELETE CASCADE,
    amazon_order_id TEXT NOT NULL,
    amazon_asin TEXT,
    amazon_description TEXT,
    amazon_price NUMERIC(10,2),
    amazon_date DATE,
    linked_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_item_amazon_item ON item_amazon_link(item_id);
CREATE UNIQUE INDEX IF NOT EXISTS idx_item_amazon_unique
    ON item_amazon_link (item_id, amazon_order_id, COALESCE(amazon_asin, ''));
