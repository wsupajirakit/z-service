import { createFileRoute } from '@tanstack/react-router'
import { compact, searchText } from '../utils/search.ts'
import { withLocale } from '../i18n/withLocale.tsx'
import { RadarSummaryPage } from '../features/radar-summary/index.ts'

export const Route = createFileRoute('/radar-summary')({
  staticData: { titleKey: 'nav_radar_summary', navOrder: 40 },
  validateSearch: (raw: Record<string, unknown>): { stamp?: string } =>
    compact({ stamp: searchText(raw, 'stamp') }),
  component: withLocale(RadarSummaryRoute),
})

function RadarSummaryRoute() {
  const { stamp } = Route.useSearch()
  const navigate = Route.useNavigate()
  return (
    <RadarSummaryPage
      stamp={stamp ?? null}
      onSelect={(next) => void navigate({ search: { stamp: next } })}
    />
  )
}
