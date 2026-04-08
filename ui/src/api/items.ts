import { apiFetch, apiUpload } from './client.ts'
import type {
  ItemCategory, ItemCategoryCreate,
  ItemCreate, ItemDetail, ItemList, ItemUpdate,
  AmazonLinkItem, AmazonOrder, DocumentItem,
  LookupResult, ImageItem,
} from './types.ts'

// --- Items ---

export function fetchItems(params: {
  location_id?: number
  category?: string
  status?: string
  media_type?: string
  q?: string
  limit?: number
  offset?: number
} = {}): Promise<ItemList> {
  const qs = new URLSearchParams()
  if (params.location_id != null) qs.set('location_id', String(params.location_id))
  if (params.category) qs.set('category', params.category)
  if (params.status) qs.set('status', params.status)
  if (params.media_type) qs.set('media_type', params.media_type)
  if (params.q) qs.set('q', params.q)
  if (params.limit) qs.set('limit', String(params.limit))
  if (params.offset) qs.set('offset', String(params.offset))
  const query = qs.toString()
  return apiFetch(`/items${query ? '?' + query : ''}`)
}

export function fetchItem(id: number): Promise<ItemDetail> {
  return apiFetch(`/items/${id}`)
}

export function createItem(data: ItemCreate): Promise<ItemDetail> {
  return apiFetch('/items', {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export function updateItem(id: number, data: ItemUpdate): Promise<ItemDetail> {
  return apiFetch(`/items/${id}`, {
    method: 'PUT',
    body: JSON.stringify(data),
  })
}

export function deleteItem(id: number): Promise<void> {
  return apiFetch(`/items/${id}`, { method: 'DELETE' })
}

export function bulkUpdateItems(data: {
  item_ids: number[]
  location_id?: number
  category?: string
  status?: string
}): Promise<{ updated: number }> {
  return apiFetch('/items/bulk', {
    method: 'PATCH',
    body: JSON.stringify(data),
  })
}

// --- Images ---

export function uploadImage(itemId: number, file: File, isPrimary = false): Promise<ImageItem> {
  const form = new FormData()
  form.append('file', file)
  return apiUpload(`/items/${itemId}/images?is_primary=${isPrimary}`, form)
}

export function deleteImage(imageId: number): Promise<void> {
  return apiFetch(`/images/${imageId}`, { method: 'DELETE' })
}

export function attachImmichImage(itemId: number, assetId: string): Promise<ImageItem> {
  return apiFetch(`/items/${itemId}/images/immich?immich_asset_id=${encodeURIComponent(assetId)}`, {
    method: 'POST',
  })
}

export function searchImmich(query: string, limit = 24): Promise<{ id: string; thumbnail_url: string; original_filename: string }[]> {
  return apiFetch(`/immich/search?q=${encodeURIComponent(query)}&limit=${limit}`)
}

export function searchImmichRecent(days = 7, limit = 24): Promise<{ id: string; thumbnail_url: string; original_filename: string }[]> {
  return apiFetch(`/immich/search/recent?days=${days}&limit=${limit}`)
}

// --- Documents ---

export function linkDocument(
  itemId: number,
  paperlessDocId: number,
  docType = 'receipt',
  description?: string,
): Promise<DocumentItem> {
  return apiFetch(`/items/${itemId}/documents`, {
    method: 'POST',
    body: JSON.stringify({
      paperless_document_id: paperlessDocId,
      document_type: docType,
      description,
    }),
  })
}

export function unlinkDocument(docId: number): Promise<void> {
  return apiFetch(`/documents/${docId}`, { method: 'DELETE' })
}

// --- Categories ---

export function fetchCategories(): Promise<ItemCategory[]> {
  return apiFetch('/categories')
}

export function createCategory(data: ItemCategoryCreate): Promise<ItemCategory> {
  return apiFetch('/categories', {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export function deleteCategory(id: number): Promise<void> {
  return apiFetch(`/categories/${id}`, { method: 'DELETE' })
}

// --- Amazon ---

export function searchAmazon(params: { q?: string; asin?: string }): Promise<AmazonOrder[]> {
  const qs = new URLSearchParams()
  if (params.q) qs.set('q', params.q)
  if (params.asin) qs.set('asin', params.asin)
  return apiFetch(`/amazon/search?${qs}`)
}

export function linkAmazon(
  itemId: number,
  data: { amazon_order_id: string; amazon_asin?: string; amazon_description?: string; amazon_price?: number; amazon_date?: string },
): Promise<AmazonLinkItem> {
  return apiFetch(`/items/${itemId}/amazon`, {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export function unlinkAmazon(linkId: number): Promise<void> {
  return apiFetch(`/amazon-links/${linkId}`, { method: 'DELETE' })
}

// --- Lookup ---

export function lookupISBN(isbn: string): Promise<LookupResult> {
  return apiFetch(`/lookup/isbn/${isbn}`)
}

export function lookupBarcode(barcode: string): Promise<LookupResult> {
  return apiFetch(`/lookup/barcode/${barcode}`)
}

export function lookupMovie(q: string): Promise<LookupResult[]> {
  return apiFetch(`/lookup/movie?q=${encodeURIComponent(q)}`)
}

export function decodeBarcode(file: File): Promise<{ barcode: string; type: string }> {
  const form = new FormData()
  form.append('file', file)
  return apiUpload('/lookup/decode-barcode', form)
}
