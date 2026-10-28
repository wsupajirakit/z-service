import { Link, useRouter } from '@tanstack/react-router'
import { useMemo } from 'react'
import { collectNav } from '../app/nav.ts'
import { m } from '../paraglide/messages.js'
import { translateTitle } from '../i18n/messageKey.ts'
import { cn } from '../components/ui/cn.ts'
import { navIcons } from './navIcons.ts'

/** Page links from the route tree. Collapsed: icons only, the label moves to a tooltip. */
export function Nav({ collapsed = false, onNavigate }: {
  collapsed?: boolean
  onNavigate?: () => void
}) {
  const router = useRouter()
  const entries = useMemo(() => collectNav(router.routeTree), [router])
  return (
    <nav aria-label={m.nav_label()} data-testid="nav">
      <ul className="space-y-0.5">
        {entries.map((e) => {
          const Icon = navIcons[e.titleKey]
          const label = translateTitle(e.titleKey)
          return (
            <li key={e.to}>
              <Link
                to={e.to}
                onClick={onNavigate}
                title={collapsed ? label : undefined}
                aria-label={collapsed ? label : undefined}
                activeOptions={{ exact: e.to === '/' }}
                className={cn('flex h-9 items-center gap-3 rounded-md text-sm',
                  'font-medium text-sidebar-foreground transition-colors',
                  'hover:bg-sidebar-accent hover:text-sidebar-accent-foreground',
                  '[&.active]:bg-sidebar-accent [&.active]:text-sidebar-accent-foreground',
                  collapsed ? 'justify-center' : 'px-2.5')}
              >
                <Icon size={18} />
                {!collapsed && <span className="truncate">{label}</span>}
              </Link>
            </li>
          )
        })}
      </ul>
    </nav>
  )
}
