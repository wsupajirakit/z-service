import { useMemo, useState } from 'react'
import { m } from '../../../paraglide/messages.js'
import { Card, CardContent } from '../../../components/ui/Card.tsx'
import { PageHeader } from '../../../components/ui/PageHeader.tsx'
import { QueryState } from '../../../components/ui/QueryState.tsx'
import { Tabs } from '../../../components/ui/Tabs.tsx'
import { useWatchlist } from '../api.ts'
import { listCounts, toRows } from '../model.ts'
import type { Watchlists } from '../schemas.ts'
import { AddItemDialog, RenameListDialog } from './ListEditor.tsx'
import { WatchlistTable } from './WatchlistTable.tsx'

/** Tab value for every list (list names are never empty). */
const ALL = ''

function WatchlistBody({ lists }: { lists: Watchlists }) {
  const [tab, setTab] = useState(ALL)
  const list = tab === ALL ? null : tab
  const all = useMemo(() => toRows(lists), [lists])
  const counts = useMemo(() => listCounts(lists), [lists])
  return (
    <>
      <PageHeader description={m.page_desc_watchlist()}>
        {list && <RenameListDialog key={list} list={list} />}
        <AddItemDialog key={list ?? ''} lists={lists} list={list} />
      </PageHeader>
      <Tabs
        testId="list-counts"
        label={m.field_list()}
        value={tab}
        onChange={setTab}
        items={[
          { value: ALL, label: m.watchlist_all({ count: all.length }) },
          ...counts.map((c) => ({ value: c.list,
            label: m.watchlist_list_count({ list: c.list, count: c.count }) })),
        ]}
      />
      <Card>
        <CardContent className="pt-5">
          <WatchlistTable key={tab} data={all} list={list} />
        </CardContent>
      </Card>
    </>
  )
}

export function WatchlistPage() {
  const query = useWatchlist()
  return (
    <section className="space-y-6">
      <QueryState query={query}>
        {(lists) => <WatchlistBody lists={lists} />}
      </QueryState>
    </section>
  )
}
