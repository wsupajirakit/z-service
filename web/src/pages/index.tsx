import { createFileRoute } from '@tanstack/react-router'
import { withLocale } from '../i18n/withLocale.tsx'
import { OverviewPage } from '../features/symbols/index.ts'

export const Route = createFileRoute('/')({
  staticData: { titleKey: 'nav_home', navOrder: 0 },
  component: withLocale(OverviewPage),
})
