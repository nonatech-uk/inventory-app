import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useItems } from '../hooks/useItems.ts'
import LoadingSpinner from '../components/common/LoadingSpinner.tsx'

const MEDIA_TYPES = ['book', 'dvd', 'bluray', 'game', 'vinyl', 'cd']

export default function Media() {
  const [mediaType, setMediaType] = useState('')
  const [offset, setOffset] = useState(0)
  const limit = 50

  // Filter items that have a media_type set
  const { data, isLoading } = useItems({
    category: 'Media',
    media_type: mediaType || undefined,
    limit,
    offset,
  })

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-xl font-semibold">Media</h2>
        <Link
          to="/add"
          className="px-3 py-1.5 bg-accent text-white rounded-md text-sm hover:bg-accent-hover transition-colors"
        >
          Add Item
        </Link>
      </div>

      <div className="flex gap-2 mb-4">
        <button
          onClick={() => { setMediaType(''); setOffset(0) }}
          className={`px-3 py-1 rounded text-sm transition-colors ${!mediaType ? 'bg-accent text-white' : 'border border-border hover:bg-bg-hover'}`}
        >
          All
        </button>
        {MEDIA_TYPES.map((t) => (
          <button
            key={t}
            onClick={() => { setMediaType(t); setOffset(0) }}
            className={`px-3 py-1 rounded text-sm capitalize transition-colors ${mediaType === t ? 'bg-accent text-white' : 'border border-border hover:bg-bg-hover'}`}
          >
            {t}
          </button>
        ))}
      </div>

      {isLoading && <LoadingSpinner />}

      {data && (
        <>
          <div className="text-sm text-text-secondary mb-2">{data.total} item{data.total !== 1 ? 's' : ''}</div>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
            {data.items.map((item) => (
              <Link
                key={item.id}
                to={`/items/${item.id}`}
                className="bg-bg-card border border-border rounded-lg p-3 hover:border-accent/50 transition-colors flex gap-3"
              >
                {item.primary_image && (
                  <img
                    src={`/api/v1/images/${item.primary_image}/thumb`}
                    alt=""
                    className="w-16 h-20 object-cover rounded shrink-0"
                  />
                )}
                <div className="min-w-0">
                  <div className="font-medium text-sm truncate">{item.media_title || item.name}</div>
                  {item.media_creator && (
                    <div className="text-xs text-text-secondary truncate">{item.media_creator}</div>
                  )}
                  <div className="text-xs text-text-secondary capitalize mt-1">{item.media_type}</div>
                </div>
              </Link>
            ))}
          </div>

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
