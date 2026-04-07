export default function StatCard({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="bg-bg-card border border-border rounded-lg p-4">
      <div className="text-sm text-text-secondary">{label}</div>
      <div className="text-2xl font-semibold mt-1 tabular-nums">{value}</div>
    </div>
  )
}
