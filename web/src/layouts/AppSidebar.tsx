import { useSyncExternalStore } from 'react'
import { m } from '../paraglide/messages.js'
import { isSidebarCollapsed, subscribeSidebar, toggleSidebar } from '../stores/sidebar.ts'
import { cn } from '../components/ui/cn.ts'
import { button } from '../components/ui/form.ts'
import { ActivityIcon, PanelLeftIcon } from '../components/ui/icons.tsx'
import { Nav } from './Nav.tsx'

export function useSidebarCollapsed() {
  return useSyncExternalStore(subscribeSidebar, isSidebarCollapsed, () => false)
}

/** App name with its mark; the name hides when the sidebar is collapsed. */
export function Brand({ collapsed = false }: { collapsed?: boolean }) {
  return (
    <span className="flex items-center gap-2 font-semibold tracking-tight">
      <span className="grid size-8 place-items-center rounded-lg bg-primary
        text-primary-foreground shadow-sm">
        <ActivityIcon size={18} />
      </span>
      {!collapsed && (
        <span className="flex flex-col leading-tight">
          <span>{m.app_title()}</span>
          <span className="text-xs font-normal text-muted-foreground">{m.app_tagline()}</span>
        </span>
      )}
    </span>
  )
}

/** Desktop sidebar (md and up): icons + labels, or icons only when collapsed. */
export function AppSidebar() {
  const collapsed = useSidebarCollapsed()
  return (
    <aside
      data-collapsed={collapsed}
      data-testid="sidebar"
      className={cn('sticky top-0 hidden h-dvh shrink-0 flex-col border-r border-sidebar-border',
        'bg-sidebar text-sidebar-foreground transition-[width] duration-200 md:flex',
        collapsed ? 'w-16' : 'w-64')}
    >
      <div className={cn('flex h-14 items-center border-b border-sidebar-border',
        collapsed ? 'justify-center' : 'px-3')}>
        <Brand collapsed={collapsed} />
      </div>
      <div className="flex-1 overflow-y-auto p-2">
        <Nav collapsed={collapsed} />
      </div>
      <div className={cn('border-t border-sidebar-border p-2', collapsed && 'flex justify-center')}>
        <button type="button" onClick={toggleSidebar} aria-expanded={!collapsed}
          aria-label={collapsed ? m.sidebar_expand() : m.sidebar_collapse()}
          title={collapsed ? m.sidebar_expand() : m.sidebar_collapse()}
          className={collapsed ? button('ghost', 'icon') : button('ghost', 'sm', 'block')}>
          <PanelLeftIcon />
          {!collapsed && m.sidebar_collapse()}
        </button>
      </div>
    </aside>
  )
}
