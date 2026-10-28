import { describe, expect, it } from 'vitest'
import { renderPage } from '../../testing/mocks/renderPage.tsx'
import { inboundEventsQuery } from './api.ts'
import { InboundEventsPage } from './components/InboundEventsPage.tsx'
import { inboundEventsSchema } from './schemas.ts'

describe('inbound events', () => {
  const rows = inboundEventsSchema.parse([{
    sender: 'engine', webhook_id: 'msg_1', event_id: 'e1', type: 'run.completed',
    source: 'https://engine.test/v1/projects/p', subject: 'runs/r1', time: null,
    link: 'https://engine.test/projects/p?tab=runs&run=r1',
    received_at: '2026-10-25T00:00:00+00:00', data: { run_id: 'r1' },
  }])

  it('lists events with a link to the result where it was produced', () => {
    const html = renderPage(<InboundEventsPage />, [[inboundEventsQuery.queryKey, rows]])
    expect(html).toContain('data-testid="inbound-events"')
    expect(html).toContain('run.completed')
    expect(html).toContain('href="https://engine.test/projects/p?tab=runs&amp;run=r1"')
  })
})
