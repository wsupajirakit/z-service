import { createFileRoute } from '@tanstack/react-router'
import { withLocale } from '../i18n/withLocale.tsx'
import { EarningScanPage } from '../features/earning-scan/index.ts'

export const Route = createFileRoute('/earning-scan')({
  staticData: { titleKey: 'nav_earning_scan', navOrder: 60 },
  component: withLocale(EarningScanPage),
})
