import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useCreateItem, useCategories } from '../hooks/useItems.ts'
import { useLocationTree } from '../hooks/useLocations.ts'
import type { LocationItem } from '../api/types.ts'
import { lookupISBN, lookupBarcode } from '../api/items.ts'
import BarcodeScanner from '../components/common/BarcodeScanner.tsx'
import type { ItemCreate } from '../api/types.ts'
const MEDIA_TYPES = ['book', 'dvd', 'bluray', 'game', 'vinyl', 'cd']

export default function AddItem() {
  const navigate = useNavigate()
  const createMutation = useCreateItem()
  const { data: locationTree } = useLocationTree()
  const { data: categories } = useCategories()

  // Flatten tree into indented options for the dropdown
  const flatLocations: { id: number; label: string }[] = []
  const flattenTree = (nodes: LocationItem[], depth = 0) => {
    for (const node of nodes) {
      flatLocations.push({ id: node.id, label: '\u00A0\u00A0'.repeat(depth) + node.name })
      if (node.children?.length) flattenTree(node.children, depth + 1)
    }
  }
  if (locationTree) flattenTree(locationTree)

  const [form, setForm] = useState<ItemCreate>({ name: '' })
  const [barcodeInput, setBarcodeInput] = useState('')
  const [lookupStatus, setLookupStatus] = useState('')
  const [showScanner, setShowScanner] = useState(false)

  const set = (fields: Partial<ItemCreate>) => setForm({ ...form, ...fields })

  const handleLookup = async (code?: string) => {
    const barcode = (code || barcodeInput).trim()
    if (!barcode) return
    setLookupStatus('Looking up...')
    try {
      // Try ISBN first (10 or 13 digits)
      const isISBN = /^(978|979)?\d{9}[\dXx]$/.test(barcode.replace(/-/g, ''))
      const result = isISBN
        ? await lookupISBN(barcode.replace(/-/g, ''))
        : await lookupBarcode(barcode)

      set({
        name: result.title || result.name || form.name,
        description: result.description || form.description,
        brand: result.brand || form.brand,
        barcode,
        media_type: isISBN ? 'book' : form.media_type,
        media_title: result.title || form.media_title,
        media_creator: result.creator || form.media_creator,
        media_isbn: isISBN ? barcode : form.media_isbn,
        media_cover_url: result.cover_url || result.image_url || form.media_cover_url,
        media_subtitle: result.subtitle || form.media_subtitle,
        media_publisher: result.publisher || form.media_publisher,
        media_pages: result.pages || form.media_pages,
        media_format: result.physical_format || form.media_format,
        media_language: result.language || form.media_language,
        media_publish_date: result.publish_date || form.media_publish_date,
        media_genre: result.subjects?.slice(0, 3).join(', ') || form.media_genre,
        category: isISBN ? 'Media' : (result.category || form.category),
      })
      setLookupStatus('Found!')
    } catch {
      setLookupStatus('Not found')
    }
  }

  const handleSubmit = () => {
    if (!form.name.trim()) return
    createMutation.mutate(form, {
      onSuccess: (item) => navigate(`/items/${item.id}`),
    })
  }

  const inputClass = "w-full border border-border rounded px-3 py-1.5 text-sm bg-bg-primary"
  const labelClass = "text-xs text-text-secondary mb-1 block"

  return (
    <div className="max-w-2xl">
      <h2 className="text-xl font-semibold mb-4">Add Item</h2>

      {/* Barcode Lookup */}
      <div className="bg-bg-card border border-border rounded-lg p-4 mb-4">
        <h3 className="text-sm font-medium mb-2">Quick Add via Barcode / ISBN</h3>
        {showScanner ? (
          <BarcodeScanner
            onScan={(code) => {
              setBarcodeInput(code)
              setShowScanner(false)
              handleLookup(code)
            }}
            onClose={() => setShowScanner(false)}
          />
        ) : (
          <div className="flex gap-2">
            <input
              placeholder="Enter barcode or ISBN..."
              value={barcodeInput}
              onChange={(e) => setBarcodeInput(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleLookup()}
              className={inputClass}
            />
            <button
              onClick={() => handleLookup()}
              className="px-4 py-1.5 bg-accent text-white rounded text-sm shrink-0 hover:bg-accent-hover"
            >
              Lookup
            </button>
            <button
              onClick={() => setShowScanner(true)}
              className="px-3 py-1.5 border border-border rounded text-sm shrink-0 hover:bg-bg-hover"
              title="Scan barcode with camera"
            >
              <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="w-5 h-5">
                <path d="M3 7V5a2 2 0 012-2h2M17 3h2a2 2 0 012 2v2M21 17v2a2 2 0 01-2 2h-2M7 21H5a2 2 0 01-2-2v-2" />
                <line x1="7" y1="12" x2="17" y2="12" />
              </svg>
            </button>
          </div>
        )}
        {lookupStatus && (
          <div className="text-xs text-text-secondary mt-1">{lookupStatus}</div>
        )}
      </div>

      {/* Main Form */}
      <div className="bg-bg-card border border-border rounded-lg p-4 space-y-4">
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className={labelClass}>Name *</label>
            <input value={form.name} onChange={(e) => set({ name: e.target.value })} className={inputClass} />
          </div>
          <div>
            <label className={labelClass}>Category</label>
            <select value={form.category || ''} onChange={(e) => set({ category: e.target.value || null })} className={inputClass}>
              <option value="">Select...</option>
              {categories?.map((c) => <option key={c.id} value={c.name}>{c.name}</option>)}
            </select>
          </div>
        </div>

        <div>
          <label className={labelClass}>Description</label>
          <textarea value={form.description || ''} onChange={(e) => set({ description: e.target.value || null })} className={inputClass} rows={2} />
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className={labelClass}>Location</label>
            <select value={form.location_id ?? ''} onChange={(e) => set({ location_id: e.target.value ? Number(e.target.value) : null })} className={inputClass}>
              <option value="">Select...</option>
              {flatLocations.map((l) => <option key={l.id} value={l.id}>{l.label}</option>)}
            </select>
          </div>
          <div>
            <label className={labelClass}>Quantity</label>
            <input type="number" min={1} value={form.quantity ?? 1} onChange={(e) => set({ quantity: Number(e.target.value) })} className={inputClass} />
          </div>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <div>
            <label className={labelClass}>Brand</label>
            <input value={form.brand || ''} onChange={(e) => set({ brand: e.target.value || null })} className={inputClass} />
          </div>
          <div>
            <label className={labelClass}>Model</label>
            <input value={form.model || ''} onChange={(e) => set({ model: e.target.value || null })} className={inputClass} />
          </div>
          <div>
            <label className={labelClass}>Serial Number</label>
            <input value={form.serial_number || ''} onChange={(e) => set({ serial_number: e.target.value || null })} className={inputClass} />
          </div>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <div>
            <label className={labelClass}>Purchase Date</label>
            <input type="date" value={form.purchase_date || ''} onChange={(e) => set({ purchase_date: e.target.value || null })} className={inputClass} />
          </div>
          <div>
            <label className={labelClass}>Purchase Price</label>
            <input type="number" step="0.01" value={form.purchase_price ?? ''} onChange={(e) => set({ purchase_price: e.target.value ? Number(e.target.value) : null })} className={inputClass} />
          </div>
          <div>
            <label className={labelClass}>Current Value</label>
            <input type="number" step="0.01" value={form.current_value ?? ''} onChange={(e) => set({ current_value: e.target.value ? Number(e.target.value) : null })} className={inputClass} />
          </div>
        </div>

        {/* Media Fields */}
        <div className="border-t border-border pt-4">
          <h3 className="text-sm font-medium mb-3">Media (optional)</h3>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div>
              <label className={labelClass}>Media Type</label>
              <select value={form.media_type || ''} onChange={(e) => set({ media_type: e.target.value || null })} className={inputClass}>
                <option value="">None</option>
                {MEDIA_TYPES.map((t) => <option key={t} value={t}>{t}</option>)}
              </select>
            </div>
            <div>
              <label className={labelClass}>{form.media_type === 'cd' || form.media_type === 'vinyl' ? 'Album' : 'Title'}</label>
              <input value={form.media_title || ''} onChange={(e) => set({ media_title: e.target.value || null })} className={inputClass} />
            </div>
            <div>
              <label className={labelClass}>
                {form.media_type === 'book' ? 'Author' : form.media_type === 'cd' || form.media_type === 'vinyl' ? 'Artist' : form.media_type === 'dvd' || form.media_type === 'bluray' ? 'Director' : form.media_type === 'game' ? 'Developer' : 'Creator'}
              </label>
              <input value={form.media_creator || ''} onChange={(e) => set({ media_creator: e.target.value || null })} className={inputClass} />
            </div>
          </div>

          {form.media_type && (
            <>
              {/* Row 2: type-sensitive fields */}
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mt-3">
                {form.media_type === 'book' && (
                  <div>
                    <label className={labelClass}>Subtitle</label>
                    <input value={form.media_subtitle || ''} onChange={(e) => set({ media_subtitle: e.target.value || null })} className={inputClass} />
                  </div>
                )}
                {(form.media_type === 'book') && (
                  <div>
                    <label className={labelClass}>ISBN</label>
                    <input value={form.media_isbn || ''} onChange={(e) => set({ media_isbn: e.target.value || null })} className={inputClass} />
                  </div>
                )}
                <div>
                  <label className={labelClass}>Genre</label>
                  <input value={form.media_genre || ''} onChange={(e) => set({ media_genre: e.target.value || null })} className={inputClass} />
                </div>
              </div>

              {/* Row 3: publisher/label/studio + date */}
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mt-3">
                <div>
                  <label className={labelClass}>
                    {form.media_type === 'cd' || form.media_type === 'vinyl' ? 'Label' : form.media_type === 'dvd' || form.media_type === 'bluray' ? 'Studio' : 'Publisher'}
                  </label>
                  <input value={form.media_publisher || ''} onChange={(e) => set({ media_publisher: e.target.value || null })} className={inputClass} />
                </div>
                <div>
                  <label className={labelClass}>{form.media_type === 'book' ? 'Publish Date' : 'Release Date'}</label>
                  <input type="date" value={form.media_publish_date || ''} onChange={(e) => set({ media_publish_date: e.target.value || null })} className={inputClass} />
                </div>
                {form.media_type === 'book' && (
                  <div>
                    <label className={labelClass}>Pages</label>
                    <input type="number" value={form.media_pages ?? ''} onChange={(e) => set({ media_pages: e.target.value ? Number(e.target.value) : null })} className={inputClass} />
                  </div>
                )}
              </div>

              {/* Row 4: book-specific extras */}
              {form.media_type === 'book' && (
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mt-3">
                  <div>
                    <label className={labelClass}>Format</label>
                    <input value={form.media_format || ''} onChange={(e) => set({ media_format: e.target.value || null })} className={inputClass} placeholder="Paperback / Hardcover" />
                  </div>
                  <div>
                    <label className={labelClass}>Language</label>
                    <input value={form.media_language || ''} onChange={(e) => set({ media_language: e.target.value || null })} className={inputClass} />
                  </div>
                </div>
              )}
            </>
          )}
        </div>

        <div>
          <label className={labelClass}>Notes</label>
          <textarea value={form.notes || ''} onChange={(e) => set({ notes: e.target.value || null })} className={inputClass} rows={2} />
        </div>

        <div className="flex gap-2 pt-2">
          <button
            onClick={handleSubmit}
            disabled={createMutation.isPending || !form.name.trim()}
            className="px-4 py-2 bg-accent text-white rounded-md text-sm hover:bg-accent-hover disabled:opacity-50"
          >
            {createMutation.isPending ? 'Saving...' : 'Save Item'}
          </button>
          <button
            onClick={() => navigate(-1)}
            className="px-4 py-2 border border-border rounded-md text-sm hover:bg-bg-hover"
          >
            Cancel
          </button>
        </div>
      </div>
    </div>
  )
}
