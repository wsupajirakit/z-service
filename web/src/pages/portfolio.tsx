import { createFileRoute } from '@tanstack/react-router'
import { withLocale } from '../i18n/withLocale.tsx'
import { PortfolioPage } from '../features/portfolio/index.ts'

export const Route = createFileRoute('/portfolio')({
  staticData: { titleKey: 'nav_portfolio', navOrder: 20 },
  component: withLocale(PortfolioPage),
})
