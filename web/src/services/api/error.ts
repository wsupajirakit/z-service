// Error type and retry policy, split from client.ts so the query client (first load) does not
// pull in the fetch/CSRF code that only pages need.
export type ErrorParams = Readonly<Record<string, string | number>>

/** A non-2xx answer. `code`/`params` come from the backend's ApiError (zservice/core/errors.py)
 * and are translated by errorMessages.ts; `detail` is the server text, shown when the code is
 * unknown (or absent: legacy routes and FastAPI validation errors). */
export class ApiError extends Error {
  readonly status: number
  readonly detail: string | null
  readonly code: string | null
  readonly params: ErrorParams

  constructor(status: number, detail: string | null, code: string | null = null,
    params: ErrorParams = {}) {
    super(detail ? `HTTP ${status}: ${detail}` : `HTTP ${status}`)
    this.name = 'ApiError'
    this.status = status
    this.detail = detail
    this.code = code
    this.params = params
  }
}

/** Retry network and 5xx errors only; 4xx answers will not change on retry. */
export function shouldRetry(failureCount: number, error: unknown): boolean {
  if (error instanceof ApiError && error.status < 500) return false
  return failureCount < 2
}
