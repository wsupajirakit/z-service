// Desktop sidebar: expanded (icons + labels) or collapsed (icons only), kept in a cookie so
// the layout is the same after a reload. The mobile drawer is page state, not stored.
import { readCookie, writeCookie } from '../utils/cookie.ts'

const COOKIE = 'zs_sidebar'
const listeners = new Set<() => void>()
let collapsed = readCookie(COOKIE) === 'collapsed'

export function isSidebarCollapsed(): boolean {
  return collapsed
}

export function toggleSidebar(): void {
  collapsed = !collapsed
  writeCookie(COOKIE, collapsed ? 'collapsed' : 'expanded')
  listeners.forEach((fn) => fn())
}

export function subscribeSidebar(fn: () => void): () => void {
  listeners.add(fn)
  return () => listeners.delete(fn)
}
