// Builds API URLs from the configured base. No other module knows the API prefix.
import { appEnv } from '../../config/env.ts'

const FALLBACK_ORIGIN = 'http://localhost'

export function currentOrigin(): string {
  return globalThis.location?.origin ?? FALLBACK_ORIGIN
}

export function apiUrl(path: string, query?: Record<string, unknown>): URL {
  const base = new URL(appEnv.apiBase, currentOrigin())
  const url = new URL(path.replace(/^\//, ''), base)
  for (const [key, value] of Object.entries(query ?? {})) {
    if (value !== undefined && value !== null) url.searchParams.set(key, String(value))
  }
  return url
}

/** Mock and test handlers match on the same URLs the client calls. */
export function apiPattern(path: string): string {
  return apiUrl(path).toString()
}

/** Same-origin href for plain `<a href download>` links (file exports). */
export function apiHref(path: string, query?: Record<string, unknown>): string {
  const url = apiUrl(path, query)
  return url.origin === currentOrigin() ? `${url.pathname}${url.search}` : url.toString()
}
