// The browser tab title follows the page and the selected language: "<page> · z-service".
// The page name comes from the deepest matched route's staticData.titleKey (same key as nav).
import { useMatches } from '@tanstack/react-router'
import { useEffect } from 'react'
import { m } from '../paraglide/messages.js'
import { translateTitle } from '../i18n/messageKey.ts'

export function pageTitle(titleKey: Parameters<typeof translateTitle>[0] | undefined): string {
  return titleKey ? `${translateTitle(titleKey)} · ${m.app_title()}` : m.app_title()
}

/** Title key of the deepest matched route (page title in the header and the browser tab). */
export function usePageTitleKey() {
  return useMatches().findLast((match) => match.staticData.titleKey)?.staticData.titleKey
}

export function useDocumentTitle(locale: string): void {
  const titleKey = usePageTitleKey()
  useEffect(() => {
    document.title = pageTitle(titleKey)
  }, [titleKey, locale])
}
