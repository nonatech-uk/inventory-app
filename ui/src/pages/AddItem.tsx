import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useCreateItem, useCategories } from '../hooks/useItems.ts'
import { useLocations } from '../hooks/useLocations.ts'
import { lookupISBN, lookupBarcode } from '../api/items.ts'
import type { ItemCreate } from '../api/types.ts'
const MEDIA_TYPES = ['book', 'dvd', 'bluray', 'game', 'vinyl', 'cd']

export default function AddItem() {
  const navigate = useNavigate()
  const createMutation = useCreateItem()
  const { data: locations } = useLocations()
  const { data: categories } = useCategories()

  const [form, setForm] = useState<ItemCreate>({ name: '' })
  const [barcodeInput, setBarcodeInput] = useState('')
  const [lookupStatus, setLookupStatus] = useState('')

  const set = (fields: Partial<ItemCreate>) => setForm({ ...form, ...fields })

  const handleLookup = async () => {
    if (!barcodeInput.trim()) return
    setLookupStatus('Looking up...')
    try {
      // Try ISBN first (10 or 13 digits)
      const isISBN = /^(978|979)?\d{9}[\dXx]$/.test(barcodeInput.replace(/-/g, ''))
      const result = isISBN
        ? await lookupISBN(barcodeInput.replace(/-/g, ''))
        : await lookupBarcode(barcodeInput)

      set({
        name: result.title || result.name || form.name,
        brand: result.brand || form.brand,
        barcode: barcodeInput,
        media_type: isISBN ? 'book' : form.media_type,
        media_title: result.title || form.media_title,
        media_creator: result.creator || form.media_creator,
        media_isbn: isISBN ? barcodeInput : form.media_isbn,
        media_cover_url: result.cover_url || result.image_url || form.media_cover_url,
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
        <div className="flex gap-2">
          <input
            placeholder="Enter barcode or ISBN..."
            value={barcodeInput}
            onChange={(e) => setBarcodeInput(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleLookup()}
            className={inputClass}
          />
          <button
            onClick={handleLookup}
            className="px-4 py-1.5 bg-accent text-white rounded text-sm shrink-0 hover:bg-accent-hover"
          >
            Lookup
          </button>
        </div>
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
              {locations?.map((l) => <option key={l.id} value={l.id}>{l.name}</option>)}
            </select>
          </div>
          <div>
            <label className={labelClass}>Quantity</label>
            <input type="number" min={1} value={form.quantity ?? 1} onChange={(e) => set({ quantity: Number(e.target.value) })} className={inputClass} />
          </div>
        </div>

        <div className="grid grid-cols-3 gap-4">
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

        <div className="grid grid-cols-3 gap-4">
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
          <div className="grid grid-cols-3 gap-4">
            <div>
              <label className={labelClass}>Media Type</label>
              <select value={form.media_type || ''} onChange={(e) => set({ media_type: e.target.value || null })} className={inputClass}>
                <option value="">None</option>
                {MEDIA_TYPES.map((t) => <option key={t} value={t}>{t}</option>)}
              </select>
            </div>
            <div>
              <label className={labelClass}>Title</label>
              <input value={form.media_title || ''} onChange={(e) => set({ media_title: e.target.value || null })} className={inputClass} />
            </div>
            <div>
              <label className={labelClass}>Creator</label>
              <input value={form.media_creator || ''} onChange={(e) => set({ media_creator: e.target.value || null })} className={inputClass} placeholder="Author / Director" />
            </div>
          </div>
          <div className="grid grid-cols-3 gap-4 mt-3">
            <div>
              <label className={labelClass}>Year</label>
              <input type="number" value={form.media_year ?? ''} onChange={(e) => set({ media_year: e.target.value ? Number(e.target.value) : null })} className={inputClass} />
            </div>
            <div>
              <label className={labelClass}>ISBN</label>
              <input value={form.media_isbn || ''} onChange={(e) => set({ media_isbn: e.target.value || null })} className={inputClass} />
            </div>
            <div>
              <label className={labelClass}>Genre</label>
              <input value={form.media_genre || ''} onChange={(e) => set({ media_genre: e.target.value || null })} className={inputClass} />
            </div>
          </div>
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
