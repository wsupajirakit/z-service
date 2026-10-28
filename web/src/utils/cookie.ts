// Preference cookies (theme, sidebar). They hold UI choices only, never session data, and are
// readable by script on purpose: the pre-paint theme script must see them.
const ONE_YEAR_SECONDS = 365 * 24 * 60 * 60

export function readCookie(name: string): string | null {
  try {
    const prefix = `${name}=`
    const hit = document.cookie.split(/;\s*/).find((c) => c.startsWith(prefix))
    return hit ? decodeURIComponent(hit.slice(prefix.length)) : null
  } catch {
    // no document (tests) or an opaque origin
    return null
  }
}

/** Site-wide, same-site only, Secure on https, kept for a year. */
export function cookieString(name: string, value: string, https: boolean): string {
  const parts = [`${name}=${encodeURIComponent(value)}`, 'Path=/', `Max-Age=${ONE_YEAR_SECONDS}`,
    'SameSite=Strict']
  if (https) parts.push('Secure')
  return parts.join('; ')
}

export function writeCookie(name: string, value: string): void {
  try {
    document.cookie = cookieString(name, value, globalThis.location?.protocol === 'https:')
  } catch {
    // cookies blocked: the choice lasts for this document only
  }
}
