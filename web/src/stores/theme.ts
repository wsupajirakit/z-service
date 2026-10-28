// Theme store. The initial value is applied before paint by public/theme-init.js from the
// zs_theme cookie; this store only reads the attribute it set and writes the cookie back.
import { writeCookie } from '../utils/cookie.ts'

export type Theme = 'light' | 'dark'
export const THEME_COOKIE = 'zs_theme'

const listeners = new Set<() => void>()

/** Resolved theme ('light' | 'dark'); dark unless the page says otherwise. */
export function getTheme(): Theme {
  return globalThis.document?.documentElement.dataset.theme === 'light' ? 'light' : 'dark'
}

export function setTheme(theme: Theme): void {
  writeCookie(THEME_COOKIE, theme)
  document.documentElement.dataset.theme = theme
  listeners.forEach((fn) => fn())
}

export function toggleTheme(): void {
  setTheme(getTheme() === 'dark' ? 'light' : 'dark')
}

export function subscribeTheme(fn: () => void): () => void {
  listeners.add(fn)
  return () => listeners.delete(fn)
}

/** Reads a CSS variable token so charts share the same colors as the page. */
export function readToken(name: string): string {
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim()
}
