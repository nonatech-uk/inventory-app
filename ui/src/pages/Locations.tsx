import { useState } from 'react'
import { useLocationTree, useLocationTypes, useCreateLocation, useCreateLocationType, useDeleteLocationType, useUpdateLocation, useDeleteLocation } from '../hooks/useLocations.ts'
import LoadingSpinner from '../components/common/LoadingSpinner.tsx'
import type { LocationItem, LocationCreate, LocationUpdate } from '../api/types.ts'

function LocationNode({ loc, depth = 0, selectedId, onSelect }: {
  loc: LocationItem
  depth?: number
  selectedId: number | null
  onSelect: (loc: LocationItem) => void
}) {
  const [expanded, setExpanded] = useState(true)
  const hasChildren = loc.children.length > 0
  const isSelected = loc.id === selectedId

  return (
    <div>
      <div
        className={`flex items-center gap-2 px-3 py-1.5 rounded text-sm cursor-pointer ${isSelected ? 'bg-accent/10 border-l-2 border-accent' : 'hover:bg-bg-hover'}`}
        style={{ paddingLeft: `${depth * 20 + 12}px` }}
      >
        {hasChildren ? (
          <span
            className="text-xs text-text-secondary w-4 cursor-pointer"
            onClick={(e) => { e.stopPropagation(); setExpanded(!expanded) }}
          >
            {expanded ? '▼' : '▶'}
          </span>
        ) : (
          <span className="w-4" />
        )}
        <span className="font-medium flex-1" onClick={() => onSelect(loc)}>{loc.name}</span>
        <span className="text-xs text-text-secondary capitalize">({loc.type})</span>
        {loc.item_count > 0 && (
          <span className="text-xs text-accent tabular-nums">{loc.item_count}</span>
        )}
      </div>
      {expanded && hasChildren && (
        <div>
          {loc.children.map((child) => (
            <LocationNode key={child.id} loc={child} depth={depth + 1} selectedId={selectedId} onSelect={onSelect} />
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
  const deleteMutation = useDeleteLocation()
  const createTypeMutation = useCreateLocationType()
  const deleteTypeMutation = useDeleteLocationType()
  const [showForm, setShowForm] = useState(false)
  const [showTypes, setShowTypes] = useState(false)
  const [form, setForm] = useState<LocationCreate>({ name: '', type: 'room' })
  const [newTypeName, setNewTypeName] = useState('')

  // Edit panel state
  const [editLoc, setEditLoc] = useState<LocationItem | null>(null)
  const [editForm, setEditForm] = useState<LocationUpdate>({})
  const updateMutation = useUpdateLocation(editLoc?.id ?? 0)

  // Flatten tree for parent dropdown
  const flatLocations: { id: number; label: string }[] = []
  const flattenTree = (nodes: LocationItem[], depth = 0) => {
    for (const node of nodes) {
      flatLocations.push({ id: node.id, label: '\u00A0\u00A0'.repeat(depth) + node.name })
      if (node.children?.length) flattenTree(node.children, depth + 1)
    }
  }
  if (tree) flattenTree(tree)

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

  const handleSelect = (loc: LocationItem) => {
    setEditLoc(loc)
    setEditForm({ name: loc.name, type: loc.type, parent_id: loc.parent_id, floor: loc.floor, description: loc.description })
  }

  const handleUpdate = () => {
    if (!editLoc) return
    updateMutation.mutate(editForm, {
      onSuccess: () => setEditLoc(null),
    })
  }

  const handleDelete = () => {
    if (!editLoc) return
    if (editLoc.children.length > 0) return
    deleteMutation.mutate(editLoc.id, {
      onSuccess: () => setEditLoc(null),
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

  const inputClass = "border border-border rounded px-3 py-1.5 text-sm bg-bg-primary w-full"
  const labelClass = "text-xs text-text-secondary mb-1 block"

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
          <div className="grid grid-cols-3 gap-3">
            <input
              placeholder="Name"
              value={form.name}
              onChange={(e) => setForm({ ...form, name: e.target.value })}
              className={inputClass}
            />
            <select
              value={form.type}
              onChange={(e) => setForm({ ...form, type: e.target.value })}
              className={inputClass}
            >
              {types?.map((t) => (
                <option key={t.id} value={t.name}>{t.name}</option>
              ))}
            </select>
            <select
              value={form.parent_id ?? ''}
              onChange={(e) => setForm({ ...form, parent_id: e.target.value ? Number(e.target.value) : null })}
              className={inputClass}
            >
              <option value="">No parent (top level)</option>
              {flatLocations.map((l) => (
                <option key={l.id} value={l.id}>{l.label}</option>
              ))}
            </select>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <input
              placeholder="Floor (optional)"
              value={form.floor || ''}
              onChange={(e) => setForm({ ...form, floor: e.target.value || null })}
              className={inputClass}
            />
            <input
              placeholder="Description (optional)"
              value={form.description || ''}
              onChange={(e) => setForm({ ...form, description: e.target.value || null })}
              className={inputClass}
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

      <div className="flex gap-4">
        {/* Tree */}
        <div className="flex-1 bg-bg-card border border-border rounded-lg py-2">
          {tree && tree.length > 0 ? (
            tree.map((loc) => (
              <LocationNode key={loc.id} loc={loc} selectedId={editLoc?.id ?? null} onSelect={handleSelect} />
            ))
          ) : (
            <div className="p-4 text-sm text-text-secondary">
              No locations yet. Add your first room or space above.
            </div>
          )}
        </div>

        {/* Edit Panel */}
        {editLoc && (
          <div className="w-80 bg-bg-card border border-border rounded-lg p-4 space-y-3 self-start">
            <h3 className="text-sm font-medium">Edit Location</h3>
            <div>
              <label className={labelClass}>Name</label>
              <input
                value={editForm.name || ''}
                onChange={(e) => setEditForm({ ...editForm, name: e.target.value })}
                className={inputClass}
              />
            </div>
            <div>
              <label className={labelClass}>Type</label>
              <select
                value={editForm.type || ''}
                onChange={(e) => setEditForm({ ...editForm, type: e.target.value })}
                className={inputClass}
              >
                {types?.map((t) => (
                  <option key={t.id} value={t.name}>{t.name}</option>
                ))}
              </select>
            </div>
            <div>
              <label className={labelClass}>Parent</label>
              <select
                value={editForm.parent_id ?? ''}
                onChange={(e) => setEditForm({ ...editForm, parent_id: e.target.value ? Number(e.target.value) : null })}
                className={inputClass}
              >
                <option value="">No parent (top level)</option>
                {flatLocations.filter((l) => l.id !== editLoc.id).map((l) => (
                  <option key={l.id} value={l.id}>{l.label}</option>
                ))}
              </select>
            </div>
            <div>
              <label className={labelClass}>Floor</label>
              <input
                value={editForm.floor || ''}
                onChange={(e) => setEditForm({ ...editForm, floor: e.target.value || null })}
                className={inputClass}
              />
            </div>
            <div>
              <label className={labelClass}>Description</label>
              <input
                value={editForm.description || ''}
                onChange={(e) => setEditForm({ ...editForm, description: e.target.value || null })}
                className={inputClass}
              />
            </div>
            <div className="flex gap-2 pt-1">
              <button
                onClick={handleUpdate}
                disabled={updateMutation.isPending}
                className="px-3 py-1.5 bg-accent text-white rounded text-sm hover:bg-accent-hover disabled:opacity-50"
              >
                Save
              </button>
              <button
                onClick={() => setEditLoc(null)}
                className="px-3 py-1.5 border border-border rounded text-sm hover:bg-bg-hover"
              >
                Cancel
              </button>
              {editLoc.children.length === 0 && (
                <button
                  onClick={handleDelete}
                  disabled={deleteMutation.isPending}
                  className="px-3 py-1.5 border border-red-300 text-red-600 rounded text-sm hover:bg-red-50 disabled:opacity-50 ml-auto"
                >
                  Delete
                </button>
              )}
            </div>
            {editLoc.children.length > 0 && (
              <div className="text-xs text-text-secondary">Cannot delete — has child locations</div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
