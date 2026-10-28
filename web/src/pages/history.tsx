import { createFileRoute } from '@tanstack/react-router'
import { compact, searchInt } from '../utils/search.ts'
import { withLocale } from '../i18n/withLocale.tsx'
import { HistoryPage } from '../features/history/index.ts'

export const Route = createFileRoute('/history')({
  staticData: { titleKey: 'nav_history', navOrder: 30 },
  validateSearch: (raw: Record<string, unknown>): { id?: number } =>
    compact({ id: searchInt(raw, 'id') }),
  component: withLocale(HistoryRoute),
})

function HistoryRoute() {
  const { id } = Route.useSearch()
  const navigate = Route.useNavigate()
  return (
    <HistoryPage
      selectedId={id ?? null}
      onSelect={(next) => void navigate({ search: next === null ? {} : { id: next } })}
    />
  )
}
