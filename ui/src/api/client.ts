export { apiFetch, ApiError } from '@mees/shared-ui'
import { ApiError } from '@mees/shared-ui'

const BASE_URL = '/api/v1'

export async function apiUpload<T>(path: string, formData: FormData): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    method: 'POST',
    credentials: 'include',
    body: formData,
  })
  if (!res.ok) {
    const body = await res.text()
    throw new ApiError(res.status, body)
  }
  return res.json()
}
