import { useState, useRef, useCallback } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { fetchAmazonOrders, uploadAmazonCsv } from '../api/items.ts'
import LoadingSpinner from '../components/common/LoadingSpinner.tsx'
import type { AmazonUploadResult } from '../api/types.ts'

export default function Amazon() {
  const [search, setSearch] = useState('')
  const [offset, setOffset] = useState(0)
  const limit = 50
  const queryClient = useQueryClient()

  const { data, isLoading } = useQuery({
    queryKey: ['amazon-orders', search, offset],
    queryFn: () => fetchAmazonOrders({ q: search || undefined, limit, offset }),
  })

  const [uploading, setUploading] = useState(false)
  const [uploadResult, setUploadResult] = useState<AmazonUploadResult | null>(null)
  const [uploadError, setUploadError] = useState<string | null>(null)
  const [dragOver, setDragOver] = useState(false)
  const fileRef = useRef<HTMLInputElement>(null)

  const handleUpload = useCallback(async (file: File) => {
    setUploading(true)
    setUploadResult(null)
    setUploadError(null)
    try {
      const result = await uploadAmazonCsv(file)
      setUploadResult(result)
      queryClient.invalidateQueries({ queryKey: ['amazon-orders'] })
    } catch (e: any) {
      setUploadError(e.message || 'Upload failed')
    } finally {
      setUploading(false)
      if (fileRef.current) fileRef.current.value = ''
    }
  }, [queryClient])

  const onFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file) handleUpload(file)
  }

  const onDrop = (e: React.DragEvent) => {
    e.preventDefault()
    setDragOver(false)
    const file = e.dataTransfer.files[0]
    if (file) handleUpload(file)
  }

  const fmt = (v: number | null) =>
    v != null ? new Intl.NumberFormat('en-GB', { style: 'currency', currency: 'GBP' }).format(v) : ''

  const totalPages = data ? Math.ceil(data.total / limit) : 0
  const currentPage = Math.floor(offset / limit) + 1

  return (
    <div>
      <h2 className="text-xl font-semibold mb-4">Amazon Orders</h2>

      {/* Upload area */}
      <div
        className={`border-2 border-dashed rounded-lg p-6 mb-4 text-center transition-colors cursor-pointer ${
          dragOver ? 'border-accent bg-accent/5' : 'border-border hover:border-accent/50'
        }`}
        onDragOver={(e) => { e.preventDefault(); setDragOver(true) }}
        onDragLeave={() => setDragOver(false)}
        onDrop={onDrop}
        onClick={() => fileRef.current?.click()}
      >
        <input
          ref={fileRef}
          type="file"
          accept=".csv"
          onChange={onFileChange}
          className="hidden"
        />
        {uploading ? (
          <div className="text-text-secondary">Uploading...</div>
        ) : (
          <div>
            <div className="text-text-secondary mb-1">Drop Amazon order CSV here or click to browse</div>
            <div className="text-xs text-text-secondary">Idempotent — duplicates are skipped</div>
          </div>
        )}
      </div>

      {/* Upload result */}
      {uploadResult && (
        <div className="bg-green-500/10 border border-green-500/30 rounded-lg px-4 py-3 mb-4 text-sm">
          Imported <strong>{uploadResult.inserted}</strong> new items, <strong>{uploadResult.skipped}</strong> duplicates skipped ({uploadResult.total} total in file)
        </div>
      )}
      {uploadError && (
        <div className="bg-red-500/10 border border-red-500/30 rounded-lg px-4 py-3 mb-4 text-sm text-red-400">
          {uploadError}
        </div>
      )}

      {/* Search */}
      <div className="mb-4">
        <input
          type="text"
          value={search}
          onChange={(e) => { setSearch(e.target.value); setOffset(0) }}
          placeholder="Search orders..."
          className="border border-border rounded px-3 py-1.5 text-sm bg-bg-primary w-full max-w-md"
        />
      </div>

      {isLoading && <LoadingSpinner />}

      {data && (
        <>
          <div className="text-sm text-text-secondary mb-2">
            {data.total} order item{data.total !== 1 ? 's' : ''}
          </div>

          <div className="bg-bg-card border border-border rounded-lg overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="border-b border-border bg-bg-primary">
                <tr>
                  <th className="text-left px-4 py-2 font-medium text-text-secondary">Date</th>
                  <th className="text-left px-4 py-2 font-medium text-text-secondary">Description</th>
                  <th className="text-left px-4 py-2 font-medium text-text-secondary">ASIN</th>
                  <th className="text-right px-4 py-2 font-medium text-text-secondary">Price</th>
                  <th className="text-right px-4 py-2 font-medium text-text-secondary">Qty</th>
                  <th className="text-left px-4 py-2 font-medium text-text-secondary">Category</th>
                </tr>
              </thead>
              <tbody>
                {data.items.map((item) => (
                  <tr key={item.id} className="border-b border-border last:border-0 hover:bg-bg-hover">
                    <td className="px-4 py-2 whitespace-nowrap">{item.order_date ?? ''}</td>
                    <td className="px-4 py-2">{item.description}</td>
                    <td className="px-4 py-2 font-mono text-xs">
                      {item.item_url ? (
                        <a href={item.item_url} target="_blank" rel="noopener noreferrer"
                           className="text-accent hover:text-accent-hover" title="View product on Amazon">
                          {item.asin ?? ''}
                        </a>
                      ) : (item.asin ?? '')}
                    </td>
                    <td className="px-4 py-2 text-right whitespace-nowrap">{fmt(item.unit_price)}</td>
                    <td className="px-4 py-2 text-right">
                      {item.order_url ? (
                        <a href={item.order_url} target="_blank" rel="noopener noreferrer"
                           className="text-accent hover:text-accent-hover" title="View order on Amazon">
                          {item.quantity}
                        </a>
                      ) : item.quantity}
                    </td>
                    <td className="px-4 py-2 text-text-secondary">{item.category ?? ''}</td>
                  </tr>
                ))}
                {data.items.length === 0 && (
                  <tr>
                    <td colSpan={6} className="px-4 py-8 text-center text-text-secondary">
                      {search ? 'No matching orders' : 'No Amazon orders yet — upload a CSV to get started'}
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
