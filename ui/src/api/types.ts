export interface UserInfo {
  email: string
  display_name: string
  role: string
}

export interface ItemCategory {
  id: number
  name: string
  sort_order: number
}

export interface ItemCategoryCreate {
  name: string
  sort_order?: number
}

export interface LocationType {
  id: number
  name: string
  sort_order: number
}

export interface LocationTypeCreate {
  name: string
  sort_order?: number
}

export interface LocationItem {
  id: number
  name: string
  type: string
  parent_id: number | null
  description: string | null
  floor: string | null
  item_count: number
  children: LocationItem[]
}

export interface LocationCreate {
  name: string
  type?: string
  parent_id?: number | null
  description?: string | null
  floor?: string | null
}

export interface LocationUpdate {
  name?: string
  type?: string
  parent_id?: number | null
  description?: string | null
  floor?: string | null
}

export interface ItemSummary {
  id: number
  name: string
  description: string | null
  category: string | null
  quantity: number
  purchase_price: number | null
  current_value: number | null
  currency: string
  brand: string | null
  model: string | null
  status: string
  media_type: string | null
  media_title: string | null
  media_creator: string | null
  location_id: number | null
  location_name: string | null
  location_path: string | null
  primary_image: string | null
  created_at: string
}

export interface ItemDetail {
  id: number
  name: string
  description: string | null
  location_id: number | null
  location_name: string | null
  location_path: string | null
  category: string | null
  quantity: number
  purchase_date: string | null
  purchase_price: number | null
  current_value: number | null
  currency: string
  brand: string | null
  model: string | null
  serial_number: string | null
  barcode: string | null
  notes: string | null
  media_type: string | null
  media_title: string | null
  media_creator: string | null
  media_year: number | null
  media_isbn: string | null
  media_cover_url: string | null
  media_subtitle: string | null
  media_publisher: string | null
  media_pages: number | null
  media_format: string | null
  media_language: string | null
  media_publish_date: string | null
  media_genre: string | null
  is_insured: boolean
  status: string
  created_at: string
  updated_at: string
  images: ImageItem[]
  documents: DocumentItem[]
  amazon_links: AmazonLinkItem[]
  ebay_links: EbayLinkItem[]
}

export interface ItemCreate {
  name: string
  description?: string | null
  location_id?: number | null
  category?: string | null
  quantity?: number
  purchase_date?: string | null
  purchase_price?: number | null
  current_value?: number | null
  currency?: string
  brand?: string | null
  model?: string | null
  serial_number?: string | null
  barcode?: string | null
  notes?: string | null
  media_type?: string | null
  media_title?: string | null
  media_creator?: string | null
  media_year?: number | null
  media_isbn?: string | null
  media_cover_url?: string | null
  media_subtitle?: string | null
  media_publisher?: string | null
  media_pages?: number | null
  media_format?: string | null
  media_language?: string | null
  media_publish_date?: string | null
  media_genre?: string | null
  is_insured?: boolean
  status?: string
}

export interface ItemUpdate extends Partial<ItemCreate> {}

export interface ItemList {
  items: ItemSummary[]
  total: number
  has_more: boolean
}

export interface ImageItem {
  id: number
  item_id: number
  filename: string
  immich_asset_id: string | null
  is_primary: boolean
  caption: string | null
  created_at: string
}

export interface DocumentItem {
  id: number
  item_id: number
  paperless_document_id: number
  document_type: string
  description: string | null
  created_at: string
}

export interface AmazonLinkItem {
  id: number
  item_id: number
  amazon_order_id: string
  amazon_asin: string | null
  amazon_description: string | null
  amazon_price: number | null
  amazon_date: string | null
  linked_at: string
}

export interface AmazonOrder {
  order_id: string
  order_date: string | null
  asin: string | null
  description: string
  quantity: number
  unit_price: number | null
  currency: string
  category: string | null
}

export interface EbayOrder {
  ebay_order_id: string
  direction: string
  ebay_item_id: string | null
  title: string
  quantity: number
  price: number | null
  currency: string
  counterparty: string | null
  order_date: string | null
  status: string | null
  image_url: string | null
  ebay_url: string | null
}

export interface EbayLinkItem {
  id: number
  item_id: number
  ebay_order_id: string
  ebay_item_id: string | null
  ebay_title: string | null
  ebay_price: number | null
  ebay_date: string | null
  direction: string
  linked_at: string
}

export interface LookupResult {
  source: string
  title?: string
  subtitle?: string
  description?: string | null
  name?: string
  creator?: string
  brand?: string
  year?: string | null
  isbn?: string
  barcode?: string
  cover_url?: string | null
  image_url?: string | null
  category?: string
  publisher?: string | null
  pages?: number | null
  physical_format?: string | null
  language?: string | null
  publish_date?: string | null
  subjects?: string[] | null
}

export interface OverviewStats {
  total_items: number
  total_value: number
  total_locations: number
  items_by_status: Record<string, number>
  items_by_category: Record<string, number>
}

export interface LocationStat {
  location: string
  item_count: number
  total_value: number
}

export interface PathSegment {
  id: number
  name: string
}
