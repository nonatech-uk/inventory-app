import { useQuery } from '@tanstack/react-query'
import { fetchMe } from '../api/meta.ts'

export function useMe() {
  return useQuery({
    queryKey: ['auth', 'me'],
    queryFn: fetchMe,
    retry: false,
  })
}
