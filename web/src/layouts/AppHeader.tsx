import { Suspense, lazy, type ReactNode } from 'react'
import { m } from '../paraglide/messages.js'
import { translateTitle } from '../i18n/messageKey.ts'
import { usePageTitleKey } from '../hooks/useDocumentTitle.ts'
import { button } from '../components/ui/form.ts'
import { MenuIcon } from '../components/ui/icons.tsx'
import { LocaleToggle } from '../components/ui/LocaleToggle.tsx'
import { ThemeToggle } from '../components/ui/ThemeToggle.tsx'
import { UserMenu } from './UserMenu.tsx'

// Lazy: the badge needs zod/mini and the query observer, which the first paint does not.
const VersionBadge = lazy(() =>
  import('../components/ui/VersionBadge.tsx').then((mod) => ({ default: mod.VersionBadge })))

function PageTitle() {
  const titleKey = usePageTitleKey()
  return (
    <h1 className="truncate text-base font-semibold tracking-tight" data-testid="page-title">
      {titleKey ? translateTitle(titleKey) : m.app_title()}
    </h1>
  )
}

/** Header of every signed-in page: menu (mobile), page title, language, theme, account. */
export function SignedInHeader({ onOpenMenu }: { onOpenMenu: () => void }) {
  return (
    <header className="sticky top-0 z-30 flex h-14 shrink-0 items-center gap-2 border-b
      bg-background/85 px-3 backdrop-blur md:px-6">
      <button type="button" className={`${button('ghost', 'icon')} md:hidden`}
        aria-label={m.sidebar_open()} title={m.sidebar_open()} onClick={onOpenMenu}>
        <MenuIcon />
      </button>
      <PageTitle />
      <span className="ml-auto flex items-center gap-1">
        <span className="hidden sm:inline-flex">
          <Suspense fallback={null}>
            <VersionBadge />
          </Suspense>
        </span>
        <LocaleToggle />
        <ThemeToggle />
        <UserMenu />
      </span>
    </header>
  )
}

/** Header of public pages (sign-in): language and theme only, nothing that needs a session. */
export function PublicHeader({ brand }: { brand: ReactNode }) {
  return (
    <header className="flex h-14 items-center gap-2 px-4">
      {brand}
      <span className="ml-auto flex items-center gap-1">
        <LocaleToggle />
        <ThemeToggle />
      </span>
    </header>
  )
}
