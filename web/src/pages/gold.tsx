import { createFileRoute } from '@tanstack/react-router'
import { withLocale } from '../i18n/withLocale.tsx'
import { GoldPage } from '../features/gold/index.ts'

export const Route = createFileRoute('/gold')({
  staticData: { titleKey: 'nav_gold', navOrder: 70 },
  component: withLocale(GoldPage),
})
