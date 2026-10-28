import { createFileRoute } from '@tanstack/react-router'
import { withLocale } from '../i18n/withLocale.tsx'
import { JobsPage } from '../features/jobs/index.ts'

export const Route = createFileRoute('/dashboard')({
  staticData: { titleKey: 'nav_dashboard', navOrder: 5 },
  component: withLocale(JobsPage),
})
