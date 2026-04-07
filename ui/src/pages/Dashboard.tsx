import { useQuery } from '@tanstack/react-query'
import { fetchOverview, fetchStatsByLocation } from '../api/meta.ts'
import LoadingSpinner from '../components/common/LoadingSpinner.tsx'
import StatCard from '../components/common/StatCard.tsx'

export default function Dashboard() {
  const { data: stats, isLoading } = useQuery({
    queryKey: ['stats', 'overview'],
    queryFn: fetchOverview,
  })
  const { data: byLocation } = useQuery({
    queryKey: ['stats', 'by-location'],
    queryFn: fetchStatsByLocation,
  })

  if (isLoading) return <LoadingSpinner />
  if (!stats) return null

  const fmt = (v: number) =>
    new Intl.NumberFormat('en-GB', { style: 'currency', currency: 'GBP' }).format(v)

  return (
    <div>
      <h2 className="text-xl font-semibold mb-4">Dashboard</h2>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        <StatCard label="Total Items" value={stats.total_items} />
        <StatCard label="Total Value" value={fmt(stats.total_value)} />
        <StatCard label="Locations" value={stats.total_locations} />
        <StatCard label="Categories" value={Object.keys(stats.items_by_category).length} />
      </div>

      <div className="grid md:grid-cols-2 gap-6">
        {/* By Category */}
        <div className="bg-bg-card border border-border rounded-lg p-4">
          <h3 className="text-sm font-medium text-text-secondary mb-3">By Category</h3>
          <div className="space-y-2">
            {Object.entries(stats.items_by_category).map(([cat, count]) => (
              <div key={cat} className="flex justify-between text-sm">
                <span>{cat}</span>
                <span className="text-text-secondary tabular-nums">{count}</span>
              </div>
            ))}
          </div>
        </div>

        {/* By Location */}
        {byLocation && (
          <div className="bg-bg-card border border-border rounded-lg p-4">
            <h3 className="text-sm font-medium text-text-secondary mb-3">By Location</h3>
            <div className="space-y-2">
              {byLocation.map((loc) => (
                <div key={loc.location} className="flex justify-between text-sm">
                  <span>{loc.location}</span>
                  <span className="text-text-secondary tabular-nums">
                    {loc.item_count} items &middot; {fmt(loc.total_value)}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* By Status */}
        <div className="bg-bg-card border border-border rounded-lg p-4">
          <h3 className="text-sm font-medium text-text-secondary mb-3">By Status</h3>
          <div className="space-y-2">
            {Object.entries(stats.items_by_status).map(([status, count]) => (
              <div key={status} className="flex justify-between text-sm">
                <span className="capitalize">{status}</span>
                <span className="text-text-secondary tabular-nums">{count}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}
