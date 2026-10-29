const API_PREFIX = `${import.meta.env.VITE_API_URL}`

export class ApiError extends Error {
  readonly status: number

  constructor(message: string, status: number) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

function getCsrfToken(): string | null {
  const prefix = 'csrf_token='
  const cookie = document.cookie
    .split('; ')
    .find((item) => item.startsWith(prefix))

  return cookie ? decodeURIComponent(cookie.slice(prefix.length)) : null
}

type RequestOptions = Omit<RequestInit, 'body'> & {
  body?: unknown
}

export async function apiRequest<T>(
  path: string,
  options: RequestOptions = {},
): Promise<T> {
  const method = (options.method ?? 'GET').toUpperCase()
  const headers = new Headers(options.headers)

  if (options.body !== undefined) {
    headers.set('Content-Type', 'application/json')
  }

  if (!['GET', 'HEAD', 'OPTIONS'].includes(method)) {
    const csrfToken = getCsrfToken()
    if (csrfToken) headers.set('X-CSRF-Token', csrfToken)
  }

  const response = await fetch(`${API_PREFIX}${path}`, {
    ...options,
    method,
    headers,
    credentials: 'include',
    body:
      options.body === undefined
        ? undefined
        : JSON.stringify(options.body),
  })

  if (!response.ok) {
    const payload: unknown = await response.json().catch(() => null)
    const detail =
      typeof payload === 'object' &&
      payload !== null &&
      'detail' in payload &&
      typeof payload.detail === 'string'
        ? payload.detail
        : `Request failed (${response.status})`

    throw new ApiError(detail, response.status)
  }

  if (response.status === 204) return undefined as T

  return response.json() as Promise<T>
}
