import { m } from '../../../paraglide/messages.js'
import { useFormat } from '../../../hooks/useFormat.ts'
import { Card, CardContent } from '../../../components/ui/Card.tsx'
import { DataTable } from '../../../components/ui/DataTable.tsx'
import { Badge } from '../../../components/ui/Feedback.tsx'
import { button } from '../../../components/ui/form.ts'
import { ExternalLinkIcon } from '../../../components/ui/icons.tsx'
import { PageHeader } from '../../../components/ui/PageHeader.tsx'
import { QueryState } from '../../../components/ui/QueryState.tsx'
import { useInboundEvents } from '../api.ts'
import type { InboundEvent } from '../schemas.ts'

/** Results other systems reported here (signed events), newest first, each with a link to
 *  the result in the system that produced it. */
export function InboundEventsPage() {
  const query = useInboundEvents()
  const fmt = useFormat()
  return (
    <section className="space-y-6">
      <PageHeader description={m.inbound_intro()} />
      <Card>
        <CardContent className="pt-5">
          <QueryState query={query}>
            {(items) => (
              <DataTable<InboundEvent>
                testId="inbound-events"
                rows={items}
                rowKey={(r) => `${r.sender}:${r.webhook_id}`}
                columns={[
                  { id: 'time', header: m.col_time(), value: (r) => r.received_at, noSearch: true,
                    cell: (r) => fmt.dateTime(r.received_at) },
                  { id: 'sender', header: m.inbound_sender(), value: (r) => r.sender,
                    cell: (r) => <Badge tone="secondary">{r.sender}</Badge> },
                  { id: 'type', header: m.inbound_type(), value: (r) => r.type,
                    cell: (r) => <span className="font-mono text-xs">{r.type}</span> },
                  { id: 'subject', header: m.inbound_subject(), value: (r) => r.subject ?? '' },
                  { id: 'open', header: '', numeric: true, cell: (r) => (r.link
                    ? (
                      <a className={button('ghost', 'sm')} href={r.link} target="_blank"
                        rel="noreferrer noopener">
                        {m.inbound_open()}
                        <ExternalLinkIcon size={14} />
                      </a>
                    )
                    : null) },
                ]}
              />
            )}
          </QueryState>
        </CardContent>
      </Card>
    </section>
  )
}
