import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { fetchEbayOrders } from '../api/items.ts'
import LoadingSpinner from '../components/common/LoadingSpinner.tsx'

export default function Ebay() {
  const [search, setSearch] = useState('')
  const [direction, setDirection] = useState('')
  const [offset, setOffset] = useState(0)
  const limit = 50

  const { data, isLoading } = useQuery({
    queryKey: ['ebay-orders', search, direction, offset],
    queryFn: () => fetchEbayOrders({ q: search || undefined, direction: direction || undefined, limit, offset }),
  })

  const fmt = (v: number | null, currency: string) =>
    v != null ? new Intl.NumberFormat('en-GB', { style: 'currency', currency }).format(v) : ''

  const totalPages = data ? Math.ceil(data.total / limit) : 0
  const currentPage = Math.floor(offset / limit) + 1

  return (
    <div>
      <h2 className="text-xl font-semibold mb-4">eBay Orders</h2>

      {/* Filters */}
      <div className="flex gap-3 mb-4 flex-wrap">
        <input
          type="text"
          value={search}
          onChange={(e) => { setSearch(e.target.value); setOffset(0) }}
          placeholder="Search orders..."
          className="border border-border rounded px-3 py-1.5 text-sm bg-bg-primary w-full max-w-md"
        />
        <select
          value={direction}
          onChange={(e) => { setDirection(e.target.value); setOffset(0) }}
          className="border border-border rounded px-3 py-1.5 text-sm bg-bg-primary"
        >
          <option value="">All</option>
          <option value="buy">Bought</option>
          <option value="sell">Sold</option>
        </select>
      </div>

      {isLoading && <LoadingSpinner />}

      {data && (
        <>
          <div className="text-sm text-text-secondary mb-2">
            {data.total} order{data.total !== 1 ? 's' : ''}
          </div>

          <div className="bg-bg-card border border-border rounded-lg overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="border-b border-border bg-bg-primary">
                <tr>
                  <th className="text-left px-4 py-2 font-medium text-text-secondary">Date</th>
                  <th className="text-left px-4 py-2 font-medium text-text-secondary">Title</th>
                  <th className="text-left px-4 py-2 font-medium text-text-secondary">Type</th>
                  <th className="text-right px-4 py-2 font-medium text-text-secondary">Price</th>
                  <th className="text-right px-4 py-2 font-medium text-text-secondary">Qty</th>
                  <th className="text-left px-4 py-2 font-medium text-text-secondary">Counterparty</th>
                </tr>
              </thead>
              <tbody>
                {data.items.map((item) => (
                  <tr key={item.ebay_order_id} className="border-b border-border last:border-0 hover:bg-bg-hover">
                    <td className="px-4 py-2 whitespace-nowrap">{item.order_date?.split(' ')[0] ?? ''}</td>
                    <td className="px-4 py-2">
                      {item.ebay_url ? (
                        <a href={item.ebay_url} target="_blank" rel="noopener noreferrer"
                           className="text-accent hover:text-accent-hover">
                          {item.title}
                        </a>
                      ) : item.title}
                    </td>
                    <td className="px-4 py-2">
                      <span className={`inline-block px-1.5 py-0.5 rounded text-xs font-medium ${
                        item.direction === 'buy'
                          ? 'bg-blue-500/15 text-blue-400'
                          : 'bg-amber-500/15 text-amber-400'
                      }`}>
                        {item.direction === 'buy' ? 'Bought' : 'Sold'}
                      </span>
                    </td>
                    <td className="px-4 py-2 text-right whitespace-nowrap">{fmt(item.price, item.currency)}</td>
                    <td className="px-4 py-2 text-right">
                      <a href={`https://www.ebay.co.uk/mesh/ord/details?orderid=${item.ebay_order_id}`}
                         target="_blank" rel="noopener noreferrer"
                         className="text-accent hover:text-accent-hover" title="View order on eBay">
                        {item.quantity}
                      </a>
                    </td>
                    <td className="px-4 py-2 text-text-secondary">{item.counterparty ?? ''}</td>
                  </tr>
                ))}
                {data.items.length === 0 && (
                  <tr>
                    <td colSpan={6} className="px-4 py-8 text-center text-text-secondary">
                      {search || direction ? 'No matching orders' : 'No eBay orders yet'}
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="flex items-center justify-between mt-3">
              <button
                disabled={offset === 0}
                onClick={() => setOffset(Math.max(0, offset - limit))}
                className="text-sm px-3 py-1 rounded border border-border disabled:opacity-40 hover:bg-bg-hover"
              >
                Previous
              </button>
              <span className="text-sm text-text-secondary">
                Page {currentPage} of {totalPages}
              </span>
              <button
                disabled={offset + limit >= data.total}
                onClick={() => setOffset(offset + limit)}
                className="text-sm px-3 py-1 rounded border border-border disabled:opacity-40 hover:bg-bg-hover"
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
