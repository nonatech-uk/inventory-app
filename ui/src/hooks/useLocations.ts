import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { fetchLocationTree, fetchLocations, fetchLocationPath, fetchLocationTypes, createLocation, createLocationType, updateLocation, deleteLocation, deleteLocationType } from '../api/locations.ts'
import type { LocationCreate, LocationTypeCreate, LocationUpdate } from '../api/types.ts'

export function useLocationTypes() {
  return useQuery({
    queryKey: ['location-types'],
    queryFn: fetchLocationTypes,
  })
}

export function useCreateLocationType() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: LocationTypeCreate) => createLocationType(data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['location-types'] })
    },
  })
}

export function useDeleteLocationType() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: number) => deleteLocationType(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['location-types'] })
    },
  })
}

export function useLocations() {
  return useQuery({
    queryKey: ['locations'],
    queryFn: fetchLocations,
  })
}

export function useLocationTree() {
  return useQuery({
    queryKey: ['locations', 'tree'],
    queryFn: fetchLocationTree,
  })
}

export function useLocationPath(id: number | undefined) {
  return useQuery({
    queryKey: ['location-path', id],
    queryFn: () => fetchLocationPath(id!),
    enabled: !!id,
  })
}

export function useCreateLocation() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: LocationCreate) => createLocation(data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['locations'] })
    },
  })
}

export function useUpdateLocation(id: number) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: LocationUpdate) => updateLocation(id, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['locations'] })
    },
  })
}

export function useDeleteLocation() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: number) => deleteLocation(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['locations'] })
    },
  })
}
