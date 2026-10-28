import { useState } from 'react'
import { Outlet, useMatches } from '@tanstack/react-router'
import { m } from '../paraglide/messages.js'
import { useDocumentTitle } from '../hooks/useDocumentTitle.ts'
import { useLocale } from '../hooks/useLocale.ts'
import { Sheet } from '../components/ui/Dialog.tsx'
import { Toaster } from '../components/ui/Toaster.tsx'
import { PublicHeader, SignedInHeader } from './AppHeader.tsx'
import { AppSidebar, Brand } from './AppSidebar.tsx'
import { Nav } from './Nav.tsx'

function SignedInShell() {
  const [menuOpen, setMenuOpen] = useState(false)
  return (
    <div className="flex min-h-dvh">
      <AppSidebar />
      <Sheet open={menuOpen} onClose={() => setMenuOpen(false)} title={m.app_title()}>
        <Nav onNavigate={() => setMenuOpen(false)} />
      </Sheet>
      <div className="flex min-w-0 flex-1 flex-col">
        <SignedInHeader onOpenMenu={() => setMenuOpen(true)} />
        <main className="mx-auto w-full max-w-[1600px] flex-1 space-y-6 p-4 md:p-6 lg:p-8">
          <Outlet />
        </main>
      </div>
    </div>
  )
}

/** Shell of every page: sidebar + header for signed-in pages, or the minimal header on
 * public routes such as sign-in. Subscribing to the locale re-renders the shell and the
 * matched route when the language changes. */
export function RootLayout() {
  const locale = useLocale()
  const isPublic = useMatches().some((match) => match.staticData.public)
  useDocumentTitle(locale)
  return (
    <div className="min-h-dvh bg-background text-foreground" data-locale={locale}>
      {isPublic ? (
        <>
          <PublicHeader brand={<Brand />} />
          <main className="px-4 pb-12"><Outlet /></main>
        </>
      ) : <SignedInShell />}
      <Toaster />
    </div>
  )
}
