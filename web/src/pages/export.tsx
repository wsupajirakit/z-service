import { createFileRoute } from '@tanstack/react-router'
import { withLocale } from '../i18n/withLocale.tsx'
import { ExportPage } from '../features/export/index.ts'

export const Route = createFileRoute('/export')({
  staticData: { titleKey: 'nav_export', navOrder: 35 },
  component: withLocale(ExportPage),
})
