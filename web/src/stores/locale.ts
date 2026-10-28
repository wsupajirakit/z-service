// Locale store on top of the Paraglide runtime. Switching never reloads the document.
import { getLocale, locales, setLocale, type Locale } from '../paraglide/runtime.js'

const listeners = new Set<() => void>()

export const LOCALES: readonly Locale[] = locales

export function currentLocale(): Locale {
  return getLocale()
}

export function changeLocale(next: Locale): void {
  setLocale(next, { reload: false })
  document.documentElement.lang = next
  listeners.forEach((fn) => fn())
}

export function subscribeLocale(fn: () => void): () => void {
  listeners.add(fn)
  return () => listeners.delete(fn)
}
