import type { ReactNode } from 'react'
import { useLocale } from '../hooks/useLocale.ts'

/**
 * Route matches are memoized by the router, so a locale change at the root does not reach
 * page components. Wrapping a page subscribes it to the locale store: it re-renders in place
 * (same document, state kept) when the locale changes.
 */
export function withLocale(Page: () => ReactNode) {
  function Localized() {
    useLocale()
    return <Page />
  }
  Localized.displayName = `withLocale(${Page.name})`
  return Localized
}
