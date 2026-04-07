import { useState } from 'react'
import { useLocationTree, useLocationTypes, useCreateLocation, useCreateLocationType, useDeleteLocationType } from '../hooks/useLocations.ts'
import LoadingSpinner from '../components/common/LoadingSpinner.tsx'
import type { LocationItem, LocationCreate } from '../api/types.ts'

function LocationNode({ loc, depth = 0 }: { loc: LocationItem; depth?: number }) {
  const [expanded, setExpanded] = useState(true)
  const hasChildren = loc.children.length > 0

  return (
    <div>
      <div
        className="flex items-center gap-2 px-3 py-1.5 hover:bg-bg-hover rounded text-sm cursor-pointer"
        style={{ paddingLeft: `${depth * 20 + 12}px` }}
        onClick={() => setExpanded(!expanded)}
      >
        {hasChildren ? (
          <span className="text-xs text-text-secondary w-4">{expanded ? '▼' : '▶'}</span>
        ) : (
          <span className="w-4" />
        )}
        <span className="font-medium">{loc.name}</span>
        <span className="text-xs text-text-secondary capitalize">({loc.type})</span>
        {loc.item_count > 0 && (
          <span className="text-xs text-accent ml-auto tabular-nums">{loc.item_count}</span>
        )}
      </div>
      {expanded && hasChildren && (
        <div>
          {loc.children.map((child) => (
            <LocationNode key={child.id} loc={child} depth={depth + 1} />
          ))}
        </div>
      )}
    </div>
  )
}

export default function Locations() {
  const { data: tree, isLoading } = useLocationTree()
  const { data: types } = useLocationTypes()
  const createMutation = useCreateLocation()
  const createTypeMutation = useCreateLocationType()
  const deleteTypeMutation = useDeleteLocationType()
  const [showForm, setShowForm] = useState(false)
  const [showTypes, setShowTypes] = useState(false)
  const [form, setForm] = useState<LocationCreate>({ name: '', type: 'room' })
  const [newTypeName, setNewTypeName] = useState('')

  if (isLoading) return <LoadingSpinner />

  const handleCreate = () => {
    if (!form.name.trim()) return
    createMutation.mutate(form, {
      onSuccess: () => {
        setForm({ name: '', type: types?.[0]?.name || 'room' })
        setShowForm(false)
      },
    })
  }

  const handleAddType = () => {
    const name = newTypeName.trim().toLowerCase()
    if (!name) return
    const nextOrder = types ? Math.max(...types.map(t => t.sort_order), 0) + 1 : 0
    createTypeMutation.mutate({ name, sort_order: nextOrder }, {
      onSuccess: () => setNewTypeName(''),
    })
  }

  const handleDeleteType = (id: number) => {
    deleteTypeMutation.mutate(id)
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-xl font-semibold">Locations</h2>
        <div className="flex gap-2">
          <button
            onClick={() => setShowTypes(!showTypes)}
            className="px-3 py-1.5 border border-border rounded-md text-sm hover:bg-bg-hover transition-colors"
          >
            Manage Types
          </button>
          <button
            onClick={() => setShowForm(!showForm)}
            className="px-3 py-1.5 bg-accent text-white rounded-md text-sm hover:bg-accent-hover transition-colors"
          >
            Add Location
          </button>
        </div>
      </div>

      {/* Type Management */}
      {showTypes && (
        <div className="bg-bg-card border border-border rounded-lg p-4 mb-4">
          <h3 className="text-sm font-medium mb-3">Location Types</h3>
          <div className="flex flex-wrap gap-2 mb-3">
            {types?.map((t) => (
              <span key={t.id} className="inline-flex items-center gap-1.5 px-2.5 py-1 bg-bg-primary border border-border rounded text-sm capitalize">
                {t.name}
                <button
                  onClick={() => handleDeleteType(t.id)}
                  className="text-text-secondary hover:text-danger text-xs leading-none"
                  title="Delete type"
                >
                  ×
                </button>
              </span>
            ))}
          </div>
          {deleteTypeMutation.isError && (
            <div className="text-xs text-danger mb-2">
              {(deleteTypeMutation.error as Error).message?.includes('409')
                ? 'Cannot delete: type is in use by existing locations'
                : 'Failed to delete type'}
            </div>
          )}
          <div className="flex gap-2">
            <input
              placeholder="New type name..."
              value={newTypeName}
              onChange={(e) => setNewTypeName(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleAddType()}
              className="border border-border rounded px-3 py-1.5 text-sm bg-bg-primary"
            />
            <button
              onClick={handleAddType}
              disabled={!newTypeName.trim() || createTypeMutation.isPending}
              className="px-3 py-1.5 bg-accent text-white rounded text-sm hover:bg-accent-hover disabled:opacity-50"
            >
              Add
            </button>
          </div>
        </div>
      )}

      {/* Add Location */}
      {showForm && (
        <div className="bg-bg-card border border-border rounded-lg p-4 mb-4 space-y-3">
          <div className="grid grid-cols-2 gap-3">
            <input
              placeholder="Name"
              value={form.name}
              onChange={(e) => setForm({ ...form, name: e.target.value })}
              className="border border-border rounded px-3 py-1.5 text-sm bg-bg-primary"
            />
            <select
              value={form.type}
              onChange={(e) => setForm({ ...form, type: e.target.value })}
              className="border border-border rounded px-3 py-1.5 text-sm bg-bg-primary"
            >
              {types?.map((t) => (
                <option key={t.id} value={t.name}>{t.name}</option>
              ))}
            </select>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <input
              placeholder="Floor (optional)"
              value={form.floor || ''}
              onChange={(e) => setForm({ ...form, floor: e.target.value || null })}
              className="border border-border rounded px-3 py-1.5 text-sm bg-bg-primary"
            />
            <input
              placeholder="Description (optional)"
              value={form.description || ''}
              onChange={(e) => setForm({ ...form, description: e.target.value || null })}
              className="border border-border rounded px-3 py-1.5 text-sm bg-bg-primary"
            />
          </div>
          <div className="flex gap-2">
            <button
              onClick={handleCreate}
              disabled={createMutation.isPending}
              className="px-3 py-1.5 bg-accent text-white rounded text-sm hover:bg-accent-hover"
            >
              Create
            </button>
            <button
              onClick={() => setShowForm(false)}
              className="px-3 py-1.5 border border-border rounded text-sm hover:bg-bg-hover"
            >
              Cancel
            </button>
          </div>
        </div>
      )}

      <div className="bg-bg-card border border-border rounded-lg py-2">
        {tree && tree.length > 0 ? (
          tree.map((loc) => <LocationNode key={loc.id} loc={loc} />)
        ) : (
          <div className="p-4 text-sm text-text-secondary">
            No locations yet. Add your first room or space above.
          </div>
        )}
      </div>
    </div>
  )
}
