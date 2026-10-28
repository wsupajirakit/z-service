import { createFileRoute } from '@tanstack/react-router'
import { withLocale } from '../i18n/withLocale.tsx'
import { StockRadarPage } from '../features/stock-radar/index.ts'

export const Route = createFileRoute('/stock-radar')({
  staticData: { titleKey: 'nav_stock_radar', navOrder: 50 },
  component: withLocale(StockRadarPage),
})
