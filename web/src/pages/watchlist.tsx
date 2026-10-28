import { createFileRoute } from '@tanstack/react-router'
import { withLocale } from '../i18n/withLocale.tsx'
import { WatchlistPage } from '../features/watchlist/index.ts'

export const Route = createFileRoute('/watchlist')({
  staticData: { titleKey: 'nav_watchlist', navOrder: 10 },
  component: withLocale(WatchlistPage),
})
