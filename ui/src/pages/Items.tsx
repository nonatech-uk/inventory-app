import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useItems, useCategories } from '../hooks/useItems.ts'
import { useLocations } from '../hooks/useLocations.ts'
import LoadingSpinner from '../components/common/LoadingSpinner.tsx'

const STATUSES = ['owned', 'lent', 'disposed', 'sold', 'lost']

export default function Items() {
  const [locationId, setLocationId] = useState<number | undefined>()
  const [category, setCategory] = useState('')
  const [status, setStatus] = useState('')
  const [offset, setOffset] = useState(0)
  const limit = 50

  const { data, isLoading } = useItems({ location_id: locationId, category: category || undefined, status: status || undefined, limit, offset })
  const { data: locations } = useLocations()
  const { data: categories } = useCategories()

  const fmt = (v: number | null, currency: string) =>
    v != null ? new Intl.NumberFormat('en-GB', { style: 'currency', currency }).format(v) : ''

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-xl font-semibold">Items</h2>
        <Link
          to="/add"
          className="px-3 py-1.5 bg-accent text-white rounded-md text-sm hover:bg-accent-hover transition-colors"
        >
          Add Item
        </Link>
      </div>

      {/* Filters */}
      <div className="flex gap-3 mb-4 flex-wrap">
        <select
          value={locationId ?? ''}
          onChange={(e) => { setLocationId(e.target.value ? Number(e.target.value) : undefined); setOffset(0) }}
          className="border border-border rounded px-3 py-1.5 text-sm bg-bg-primary"
        >
          <option value="">All Locations</option>
          {locations?.map((l) => (
            <option key={l.id} value={l.id}>{l.name}</option>
          ))}
        </select>
        <select
          value={category}
          onChange={(e) => { setCategory(e.target.value); setOffset(0) }}
          className="border border-border rounded px-3 py-1.5 text-sm bg-bg-primary"
        >
          <option value="">All Categories</option>
          {categories?.map((c) => (
            <option key={c.id} value={c.name}>{c.name}</option>
          ))}
        </select>
        <select
          value={status}
          onChange={(e) => { setStatus(e.target.value); setOffset(0) }}
          className="border border-border rounded px-3 py-1.5 text-sm bg-bg-primary"
        >
          <option value="">All Statuses</option>
          {STATUSES.map((s) => (
            <option key={s} value={s}>{s}</option>
          ))}
        </select>
      </div>

      {isLoading && <LoadingSpinner />}

      {data && (
        <>
          <div className="text-sm text-text-secondary mb-2">
            {data.total} item{data.total !== 1 ? 's' : ''}
          </div>

          <div className="bg-bg-card border border-border rounded-lg overflow-hidden">
            <table className="w-full text-sm">
              <thead className="border-b border-border bg-bg-primary">
                <tr>
                  <th className="text-left px-4 py-2 font-medium text-text-secondary">Name</th>
                  <th className="text-left px-4 py-2 font-medium text-text-secondary">Location</th>
                  <th className="text-left px-4 py-2 font-medium text-text-secondary">Category</th>
                  <th className="text-right px-4 py-2 font-medium text-text-secondary">Value</th>
                  <th className="text-left px-4 py-2 font-medium text-text-secondary">Status</th>
                </tr>
              </thead>
              <tbody>
                {data.items.map((item) => (
                  <tr key={item.id} className="border-b border-border last:border-0 hover:bg-bg-hover">
                    <td className="px-4 py-2">
                      <Link to={`/items/${item.id}`} className="text-accent hover:underline font-medium">
                        {item.name}
                      </Link>
                      {item.brand && (
                        <span className="text-text-secondary ml-1">({item.brand})</span>
                      )}
                    </td>
                    <td className="px-4 py-2 text-text-secondary">{item.location_name || '—'}</td>
                    <td className="px-4 py-2 text-text-secondary">{item.category || '—'}</td>
                    <td className="px-4 py-2 text-right tabular-nums">{fmt(item.current_value, item.currency)}</td>
                    <td className="px-4 py-2">
                      <span className="capitalize text-text-secondary">{item.status}</span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Pagination */}
          {data.total > limit && (
            <div className="flex gap-2 mt-4 justify-center">
              <button
                disabled={offset === 0}
                onClick={() => setOffset(Math.max(0, offset - limit))}
                className="px-3 py-1 border border-border rounded text-sm disabled:opacity-40"
              >
                Previous
              </button>
              <span className="px-3 py-1 text-sm text-text-secondary">
                {offset + 1}–{Math.min(offset + limit, data.total)} of {data.total}
              </span>
              <button
                disabled={!data.has_more}
                onClick={() => setOffset(offset + limit)}
                className="px-3 py-1 border border-border rounded text-sm disabled:opacity-40"
              >
                Next
              </button>
            </div>
          )}
        </>
      )}
    </div>
  )
}
