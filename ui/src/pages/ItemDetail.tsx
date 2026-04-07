import { useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useItem, useUpdateItem, useDeleteItem, useCategories } from '../hooks/useItems.ts'
import { useLocations } from '../hooks/useLocations.ts'
import { useLocationPath } from '../hooks/useLocations.ts'
import { uploadImage, deleteImage, unlinkDocument, unlinkAmazon } from '../api/items.ts'
import { useQueryClient } from '@tanstack/react-query'
import LoadingSpinner from '../components/common/LoadingSpinner.tsx'
import type { ItemUpdate } from '../api/types.ts'

const STATUSES = ['owned', 'lent', 'disposed', 'sold', 'lost']
const MEDIA_TYPES = ['book', 'dvd', 'bluray', 'game', 'vinyl', 'cd']

export default function ItemDetail() {
  const { id } = useParams()
  const itemId = id ? Number(id) : undefined
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const { data: item, isLoading } = useItem(itemId)
  const { data: locations } = useLocations()
  const { data: categories } = useCategories()
  const { data: path } = useLocationPath(item?.location_id ?? undefined)
  const updateMutation = useUpdateItem(itemId!)
  const deleteMutation = useDeleteItem()
  const [editing, setEditing] = useState(false)
  const [editForm, setEditForm] = useState<ItemUpdate>({})

  if (isLoading) return <LoadingSpinner />
  if (!item) return <div className="text-text-secondary">Item not found</div>

  const startEdit = () => {
    setEditForm({
      name: item.name,
      description: item.description,
      location_id: item.location_id,
      category: item.category,
      quantity: item.quantity,
      purchase_date: item.purchase_date,
      purchase_price: item.purchase_price,
      current_value: item.current_value,
      brand: item.brand,
      model: item.model,
      serial_number: item.serial_number,
      barcode: item.barcode,
      notes: item.notes,
      media_type: item.media_type,
      media_title: item.media_title,
      media_creator: item.media_creator,
      media_year: item.media_year,
      media_isbn: item.media_isbn,
      media_genre: item.media_genre,
      is_insured: item.is_insured,
      status: item.status,
    })
    setEditing(true)
  }

  const saveEdit = () => {
    updateMutation.mutate(editForm, { onSuccess: () => setEditing(false) })
  }

  const handleDelete = () => {
    if (confirm('Delete this item?')) {
      deleteMutation.mutate(item.id, { onSuccess: () => navigate('/items') })
    }
  }

  const handleImageUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    await uploadImage(item.id, file, item.images.length === 0)
    queryClient.invalidateQueries({ queryKey: ['item', itemId] })
  }

  const handleImageDelete = async (imageId: number) => {
    await deleteImage(imageId)
    queryClient.invalidateQueries({ queryKey: ['item', itemId] })
  }

  const handleDocUnlink = async (docId: number) => {
    await unlinkDocument(docId)
    queryClient.invalidateQueries({ queryKey: ['item', itemId] })
  }

  const handleAmazonUnlink = async (linkId: number) => {
    await unlinkAmazon(linkId)
    queryClient.invalidateQueries({ queryKey: ['item', itemId] })
  }

  const fmt = (v: number | null) =>
    v != null ? new Intl.NumberFormat('en-GB', { style: 'currency', currency: item.currency }).format(v) : '—'

  const inputClass = "w-full border border-border rounded px-3 py-1.5 text-sm bg-bg-primary"
  const labelClass = "text-xs text-text-secondary mb-1 block"
  const set = (fields: Partial<ItemUpdate>) => setEditForm({ ...editForm, ...fields })

  return (
    <div className="max-w-3xl">
      {/* Header */}
      <div className="flex items-start justify-between mb-4">
        <div>
          <button onClick={() => navigate(-1)} className="text-sm text-text-secondary hover:text-text-primary mb-1">&larr; Back</button>
          {path && (
            <div className="text-xs text-text-secondary mb-1">
              {path.map((p, i) => (
                <span key={p.id}>{i > 0 && ' > '}{p.name}</span>
              ))}
            </div>
          )}
          <h2 className="text-xl font-semibold">{item.name}</h2>
        </div>
        <div className="flex gap-2">
          {!editing ? (
            <>
              <button onClick={startEdit} className="px-3 py-1.5 bg-accent text-white rounded text-sm hover:bg-accent-hover">Edit</button>
              <button onClick={handleDelete} className="px-3 py-1.5 border border-danger text-danger rounded text-sm hover:bg-danger/10">Delete</button>
            </>
          ) : (
            <>
              <button onClick={saveEdit} disabled={updateMutation.isPending} className="px-3 py-1.5 bg-accent text-white rounded text-sm hover:bg-accent-hover">Save</button>
              <button onClick={() => setEditing(false)} className="px-3 py-1.5 border border-border rounded text-sm hover:bg-bg-hover">Cancel</button>
            </>
          )}
        </div>
      </div>

      {/* Details */}
      <div className="bg-bg-card border border-border rounded-lg p-4 mb-4">
        {!editing ? (
          <div className="grid grid-cols-2 gap-x-6 gap-y-3 text-sm">
            <div><span className="text-text-secondary">Category:</span> {item.category || '—'}</div>
            <div><span className="text-text-secondary">Status:</span> <span className="capitalize">{item.status}</span></div>
            <div><span className="text-text-secondary">Location:</span> {item.location_name || '—'}</div>
            <div><span className="text-text-secondary">Quantity:</span> {item.quantity}</div>
            <div><span className="text-text-secondary">Brand:</span> {item.brand || '—'}</div>
            <div><span className="text-text-secondary">Model:</span> {item.model || '—'}</div>
            <div><span className="text-text-secondary">Serial:</span> {item.serial_number || '—'}</div>
            <div><span className="text-text-secondary">Barcode:</span> {item.barcode || '—'}</div>
            <div><span className="text-text-secondary">Purchase Price:</span> {fmt(item.purchase_price)}</div>
            <div><span className="text-text-secondary">Current Value:</span> {fmt(item.current_value)}</div>
            <div><span className="text-text-secondary">Purchase Date:</span> {item.purchase_date || '—'}</div>
            <div><span className="text-text-secondary">Insured:</span> {item.is_insured ? 'Yes' : 'No'}</div>
            {item.description && (
              <div className="col-span-2"><span className="text-text-secondary">Description:</span> {item.description}</div>
            )}
            {item.notes && (
              <div className="col-span-2"><span className="text-text-secondary">Notes:</span> {item.notes}</div>
            )}

            {/* Media */}
            {item.media_type && (
              <>
                <div className="col-span-2 border-t border-border pt-3 mt-1 text-xs font-medium text-text-secondary uppercase">Media Info</div>
                <div><span className="text-text-secondary">Type:</span> {item.media_type}</div>
                <div><span className="text-text-secondary">Title:</span> {item.media_title || '—'}</div>
                <div><span className="text-text-secondary">Creator:</span> {item.media_creator || '—'}</div>
                <div><span className="text-text-secondary">Year:</span> {item.media_year || '—'}</div>
                <div><span className="text-text-secondary">ISBN:</span> {item.media_isbn || '—'}</div>
                <div><span className="text-text-secondary">Genre:</span> {item.media_genre || '—'}</div>
              </>
            )}
          </div>
        ) : (
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div><label className={labelClass}>Name</label><input value={editForm.name || ''} onChange={(e) => set({ name: e.target.value })} className={inputClass} /></div>
              <div><label className={labelClass}>Category</label>
                <select value={editForm.category || ''} onChange={(e) => set({ category: e.target.value || null })} className={inputClass}>
                  <option value="">Select...</option>
                  {categories?.map((c) => <option key={c.id} value={c.name}>{c.name}</option>)}
                </select>
              </div>
            </div>
            <div><label className={labelClass}>Description</label><textarea value={editForm.description || ''} onChange={(e) => set({ description: e.target.value || null })} className={inputClass} rows={2} /></div>
            <div className="grid grid-cols-3 gap-4">
              <div><label className={labelClass}>Location</label>
                <select value={editForm.location_id ?? ''} onChange={(e) => set({ location_id: e.target.value ? Number(e.target.value) : null })} className={inputClass}>
                  <option value="">Select...</option>
                  {locations?.map((l) => <option key={l.id} value={l.id}>{l.name}</option>)}
                </select>
              </div>
              <div><label className={labelClass}>Status</label>
                <select value={editForm.status || ''} onChange={(e) => set({ status: e.target.value })} className={inputClass}>
                  {STATUSES.map((s) => <option key={s} value={s}>{s}</option>)}
                </select>
              </div>
              <div><label className={labelClass}>Quantity</label><input type="number" min={1} value={editForm.quantity ?? 1} onChange={(e) => set({ quantity: Number(e.target.value) })} className={inputClass} /></div>
            </div>
            <div className="grid grid-cols-3 gap-4">
              <div><label className={labelClass}>Brand</label><input value={editForm.brand || ''} onChange={(e) => set({ brand: e.target.value || null })} className={inputClass} /></div>
              <div><label className={labelClass}>Model</label><input value={editForm.model || ''} onChange={(e) => set({ model: e.target.value || null })} className={inputClass} /></div>
              <div><label className={labelClass}>Serial</label><input value={editForm.serial_number || ''} onChange={(e) => set({ serial_number: e.target.value || null })} className={inputClass} /></div>
            </div>
            <div className="grid grid-cols-3 gap-4">
              <div><label className={labelClass}>Purchase Date</label><input type="date" value={editForm.purchase_date || ''} onChange={(e) => set({ purchase_date: e.target.value || null })} className={inputClass} /></div>
              <div><label className={labelClass}>Purchase Price</label><input type="number" step="0.01" value={editForm.purchase_price ?? ''} onChange={(e) => set({ purchase_price: e.target.value ? Number(e.target.value) : null })} className={inputClass} /></div>
              <div><label className={labelClass}>Current Value</label><input type="number" step="0.01" value={editForm.current_value ?? ''} onChange={(e) => set({ current_value: e.target.value ? Number(e.target.value) : null })} className={inputClass} /></div>
            </div>
            {/* Media section in edit mode */}
            <div className="border-t border-border pt-3">
              <h3 className="text-sm font-medium mb-2">Media</h3>
              <div className="grid grid-cols-3 gap-4">
                <div><label className={labelClass}>Type</label>
                  <select value={editForm.media_type || ''} onChange={(e) => set({ media_type: e.target.value || null })} className={inputClass}>
                    <option value="">None</option>
                    {MEDIA_TYPES.map((t) => <option key={t} value={t}>{t}</option>)}
                  </select>
                </div>
                <div><label className={labelClass}>Title</label><input value={editForm.media_title || ''} onChange={(e) => set({ media_title: e.target.value || null })} className={inputClass} /></div>
                <div><label className={labelClass}>Creator</label><input value={editForm.media_creator || ''} onChange={(e) => set({ media_creator: e.target.value || null })} className={inputClass} /></div>
              </div>
            </div>
            <div><label className={labelClass}>Notes</label><textarea value={editForm.notes || ''} onChange={(e) => set({ notes: e.target.value || null })} className={inputClass} rows={2} /></div>
          </div>
        )}
      </div>

      {/* Images */}
      <div className="bg-bg-card border border-border rounded-lg p-4 mb-4">
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-sm font-medium">Photos</h3>
          <label className="px-3 py-1 bg-accent text-white rounded text-xs cursor-pointer hover:bg-accent-hover">
            Upload
            <input type="file" accept="image/*" onChange={handleImageUpload} className="hidden" />
          </label>
        </div>
        {item.images.length > 0 ? (
          <div className="grid grid-cols-4 gap-2">
            {item.images.map((img) => (
              <div key={img.id} className="relative group">
                <img
                  src={img.immich_asset_id ? `/api/v1/images/${img.filename}` : `/api/v1/images/${img.filename}/thumb`}
                  alt={img.caption || ''}
                  className="w-full h-24 object-cover rounded"
                />
                <button
                  onClick={() => handleImageDelete(img.id)}
                  className="absolute top-1 right-1 bg-black/50 text-white rounded-full w-5 h-5 text-xs hidden group-hover:flex items-center justify-center"
                >
                  x
                </button>
                {img.is_primary && (
                  <span className="absolute bottom-1 left-1 bg-accent text-white text-[10px] px-1 rounded">Primary</span>
                )}
              </div>
            ))}
          </div>
        ) : (
          <div className="text-sm text-text-secondary">No photos yet.</div>
        )}
      </div>

      {/* Documents */}
      {item.documents.length > 0 && (
        <div className="bg-bg-card border border-border rounded-lg p-4 mb-4">
          <h3 className="text-sm font-medium mb-3">Linked Documents</h3>
          <div className="space-y-2">
            {item.documents.map((doc) => (
              <div key={doc.id} className="flex items-center justify-between text-sm">
                <div>
                  <span className="capitalize text-text-secondary">{doc.document_type}</span>
                  {doc.description && <span className="ml-2">{doc.description}</span>}
                  <span className="text-xs text-text-secondary ml-2">#{doc.paperless_document_id}</span>
                </div>
                <button onClick={() => handleDocUnlink(doc.id)} className="text-xs text-danger hover:underline">Unlink</button>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Amazon Links */}
      {item.amazon_links.length > 0 && (
        <div className="bg-bg-card border border-border rounded-lg p-4 mb-4">
          <h3 className="text-sm font-medium mb-3">Amazon Orders</h3>
          <div className="space-y-2">
            {item.amazon_links.map((link) => (
              <div key={link.id} className="flex items-center justify-between text-sm">
                <div>
                  <span>{link.amazon_description || link.amazon_order_id}</span>
                  {link.amazon_price != null && (
                    <span className="text-text-secondary ml-2">
                      {new Intl.NumberFormat('en-GB', { style: 'currency', currency: 'GBP' }).format(link.amazon_price)}
                    </span>
                  )}
                  {link.amazon_date && (
                    <span className="text-xs text-text-secondary ml-2">{link.amazon_date}</span>
                  )}
                </div>
                <button onClick={() => handleAmazonUnlink(link.id)} className="text-xs text-danger hover:underline">Unlink</button>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="text-xs text-text-secondary">
        Created {item.created_at} &middot; Updated {item.updated_at}
      </div>
    </div>
  )
}
