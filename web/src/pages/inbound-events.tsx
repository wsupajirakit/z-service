import { createFileRoute } from '@tanstack/react-router'
import { withLocale } from '../i18n/withLocale.tsx'
import { InboundEventsPage } from '../features/inbound-events/index.ts'

export const Route = createFileRoute('/inbound-events')({
  staticData: { titleKey: 'nav_inbound_events', navOrder: 95 },
  component: withLocale(InboundEventsPage),
})
