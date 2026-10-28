// Nav entries are derived from the route tree (staticData), never from a hand-written tab list.
import type { AnyRoute } from '@tanstack/react-router'
import type { TitleKey } from '../i18n/messageKey.ts'

export type NavEntry = { to: string; titleKey: TitleKey; order: number }

export function collectNav(root: AnyRoute): NavEntry[] {
  const out: NavEntry[] = []
  const walk = (route: AnyRoute) => {
    const { titleKey, navOrder } = route.options.staticData ?? {}
    if (titleKey) out.push({ to: route.fullPath, titleKey, order: navOrder ?? 999 })
    const children = route.children as Record<string, AnyRoute> | AnyRoute[] | undefined
    Object.values(children ?? {}).forEach(walk)
  }
  walk(root)
  return out.sort((a, b) => a.order - b.order)
}
