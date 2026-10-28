import { createFileRoute } from '@tanstack/react-router'
import { withLocale } from '../i18n/withLocale.tsx'
import { SettingsPage } from '../features/settings/index.ts'

export const Route = createFileRoute('/settings')({
  staticData: { titleKey: 'nav_settings', navOrder: 90 },
  component: withLocale(SettingsPage),
})
