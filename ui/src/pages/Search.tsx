import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { useItems } from '../hooks/useItems.ts'
import LoadingSpinner from '../components/common/LoadingSpinner.tsx'

export default function Search() {
  const [query, setQuery] = useState('')
  const [debouncedQuery, setDebouncedQuery] = useState('')

  useEffect(() => {
    if (query.length < 2) {
      setDebouncedQuery('')
      return
    }
    const t = setTimeout(() => setDebouncedQuery(query), 300)
    return () => clearTimeout(t)
  }, [query])

  const { data, isLoading } = useItems(
    debouncedQuery ? { q: debouncedQuery, limit: 50 } : { limit: 0 },
  )

  const fmt = (v: number | null, currency: string) =>
    v != null ? new Intl.NumberFormat('en-GB', { style: 'currency', currency }).format(v) : ''

  return (
    <div>
      <h2 className="text-xl font-semibold mb-4">Search</h2>

      <input
        autoFocus
        placeholder="Search items..."
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        className="w-full max-w-lg border border-border rounded-lg px-4 py-2 text-sm bg-bg-primary mb-4"
      />

      {isLoading && debouncedQuery && <LoadingSpinner />}

      {data && data.items.length > 0 && (
        <div className="space-y-2">
          {data.items.map((item) => (
            <Link
              key={item.id}
              to={`/items/${item.id}`}
              className="block bg-bg-card border border-border rounded-lg p-3 hover:border-accent/50 transition-colors"
            >
              <div className="flex justify-between">
                <div>
                  <span className="font-medium text-sm">{item.name}</span>
                  {item.brand && <span className="text-text-secondary text-sm ml-1">({item.brand})</span>}
                </div>
                <span className="text-sm tabular-nums text-text-secondary">{fmt(item.current_value, item.currency)}</span>
              </div>
              <div className="text-xs text-text-secondary mt-1">
                {[item.location_name, item.category, item.status !== 'owned' ? item.status : null]
                  .filter(Boolean)
                  .join(' · ')}
              </div>
            </Link>
          ))}
          <div className="text-xs text-text-secondary">{data.total} result{data.total !== 1 ? 's' : ''}</div>
        </div>
      )}

      {data && data.items.length === 0 && debouncedQuery && (
        <div className="text-sm text-text-secondary">No results found.</div>
      )}
    </div>
  )
}
