// CSRF double-submit: the backend sets the readable cookie `__Host-zs_csrf`; every
// state-changing request echoes it in `X-ZS-CSRF`. Until the backend issues the cookie,
// nothing is sent. Only the API client uses this module.
export const CSRF_COOKIE = '__Host-zs_csrf'
export const CSRF_HEADER = 'X-ZS-CSRF'

export function readCookie(cookieHeader: string, name: string): string | null {
  for (const part of cookieHeader.split(';')) {
    const eq = part.indexOf('=')
    if (eq < 0) continue
    if (part.slice(0, eq).trim() !== name) continue
    const raw = part.slice(eq + 1).trim()
    if (raw === '') return null
    try {
      return decodeURIComponent(raw)
    } catch {
      return raw
    }
  }
  return null
}

export function csrfHeaders(cookieHeader?: string): Record<string, string> {
  const source = cookieHeader ?? (typeof document === 'undefined' ? '' : document.cookie)
  const token = readCookie(source, CSRF_COOKIE)
  return token ? { [CSRF_HEADER]: token } : {}
}
