import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { fetchItems, fetchItem, createItem, updateItem, deleteItem, fetchCategories, createCategory, deleteCategory } from '../api/items.ts'
import type { ItemCategoryCreate, ItemCreate, ItemUpdate } from '../api/types.ts'

export function useCategories() {
  return useQuery({
    queryKey: ['categories'],
    queryFn: fetchCategories,
  })
}

export function useCreateCategory() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: ItemCategoryCreate) => createCategory(data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['categories'] })
    },
  })
}

export function useDeleteCategory() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: number) => deleteCategory(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['categories'] })
    },
  })
}

export function useItems(params: {
  location_id?: number
  category?: string
  status?: string
  media_type?: string
  q?: string
  limit?: number
  offset?: number
} = {}) {
  return useQuery({
    queryKey: ['items', params],
    queryFn: () => fetchItems(params),
  })
}

export function useItem(id: number | undefined) {
  return useQuery({
    queryKey: ['item', id],
    queryFn: () => fetchItem(id!),
    enabled: !!id,
  })
}

export function useCreateItem() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: ItemCreate) => createItem(data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['items'] })
    },
  })
}

export function useUpdateItem(id: number) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: ItemUpdate) => updateItem(id, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['item', id] })
      qc.invalidateQueries({ queryKey: ['items'] })
    },
  })
}

export function useDeleteItem() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: number) => deleteItem(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['items'] })
    },
  })
}
