import createClient from 'openapi-fetch'
import type { components, paths } from './generated/schema'

export type ErrorResponse = components['schemas']['ErrorResponse']

export type ApiClient = ReturnType<typeof createClient<paths>>

type ApiClientOptions = {
  baseUrl: string
  fetch?: (input: Request) => Promise<Response>
}

export function createApiClient({ baseUrl, fetch }: ApiClientOptions) {
  return createClient<paths>({ baseUrl, fetch })
}

export const apiClient = createApiClient({
  baseUrl: import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000',
})
