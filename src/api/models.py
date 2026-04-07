"""Pydantic request/response models."""

from datetime import date, datetime

from pydantic import BaseModel


class UserInfo(BaseModel):
    email: str
    display_name: str
    role: str


# --- Location ---

class LocationItem(BaseModel):
    id: int
    name: str
    type: str
    parent_id: int | None
    description: str | None
    floor: str | None
    item_count: int = 0
    children: list["LocationItem"] = []


class LocationCreate(BaseModel):
    name: str
    type: str = "room"
    parent_id: int | None = None
    description: str | None = None
    floor: str | None = None


class LocationUpdate(BaseModel):
    name: str | None = None
    type: str | None = None
    parent_id: int | None = None
    description: str | None = None
    floor: str | None = None


# --- Item ---

class ItemSummary(BaseModel):
    id: int
    name: str
    description: str | None
    category: str | None
    quantity: int
    purchase_price: float | None
    current_value: float | None
    currency: str
    brand: str | None
    model: str | None
    status: str
    media_type: str | None
    media_title: str | None
    media_creator: str | None
    location_id: int | None
    location_name: str | None = None
    location_path: str | None = None
    primary_image: str | None = None
    created_at: str


class ItemDetail(BaseModel):
    id: int
    name: str
    description: str | None
    location_id: int | None
    location_name: str | None = None
    location_path: str | None = None
    category: str | None
    quantity: int
    purchase_date: str | None
    purchase_price: float | None
    current_value: float | None
    currency: str
    brand: str | None
    model: str | None
    serial_number: str | None
    barcode: str | None
    notes: str | None
    media_type: str | None
    media_title: str | None
    media_creator: str | None
    media_year: int | None
    media_isbn: str | None
    media_cover_url: str | None
    media_genre: str | None
    is_insured: bool
    status: str
    created_at: str
    updated_at: str
    images: list["ImageItem"] = []
    documents: list["DocumentItem"] = []
    amazon_links: list["AmazonLinkItem"] = []


class ItemCreate(BaseModel):
    name: str
    description: str | None = None
    location_id: int | None = None
    category: str | None = None
    quantity: int = 1
    purchase_date: str | None = None
    purchase_price: float | None = None
    current_value: float | None = None
    currency: str = "GBP"
    brand: str | None = None
    model: str | None = None
    serial_number: str | None = None
    barcode: str | None = None
    notes: str | None = None
    media_type: str | None = None
    media_title: str | None = None
    media_creator: str | None = None
    media_year: int | None = None
    media_isbn: str | None = None
    media_cover_url: str | None = None
    media_genre: str | None = None
    is_insured: bool = False
    status: str = "owned"


class ItemUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    location_id: int | None = None
    category: str | None = None
    quantity: int | None = None
    purchase_date: str | None = None
    purchase_price: float | None = None
    current_value: float | None = None
    currency: str | None = None
    brand: str | None = None
    model: str | None = None
    serial_number: str | None = None
    barcode: str | None = None
    notes: str | None = None
    media_type: str | None = None
    media_title: str | None = None
    media_creator: str | None = None
    media_year: int | None = None
    media_isbn: str | None = None
    media_cover_url: str | None = None
    media_genre: str | None = None
    is_insured: bool | None = None
    status: str | None = None


class ItemList(BaseModel):
    items: list[ItemSummary]
    total: int
    has_more: bool


# --- Image ---

class ImageItem(BaseModel):
    id: int
    item_id: int
    filename: str
    immich_asset_id: str | None
    is_primary: bool
    caption: str | None
    created_at: str


# --- Document ---

class DocumentItem(BaseModel):
    id: int
    item_id: int
    paperless_document_id: int
    document_type: str
    description: str | None
    created_at: str


class DocumentCreate(BaseModel):
    paperless_document_id: int
    document_type: str = "receipt"
    description: str | None = None


# --- Amazon ---

class AmazonLinkItem(BaseModel):
    id: int
    item_id: int
    amazon_order_id: str
    amazon_asin: str | None
    amazon_description: str | None
    amazon_price: float | None
    amazon_date: str | None
    linked_at: str


class AmazonLinkCreate(BaseModel):
    amazon_order_id: str
    amazon_asin: str | None = None
    amazon_description: str | None = None
    amazon_price: float | None = None
    amazon_date: str | None = None


# --- Stats ---

class OverviewStats(BaseModel):
    total_items: int
    total_value: float | None
    total_locations: int
    items_by_status: dict[str, int]
    items_by_category: dict[str, int]
    recent_items: list[ItemSummary]
