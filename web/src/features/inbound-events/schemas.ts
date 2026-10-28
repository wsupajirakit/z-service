import * as z from 'zod/mini'

// GET /api/inbound-events (backend zservice/domains/inbound_events): events other systems
// sent (CloudEvents); `data` belongs to the sender, so it stays open.
export const inboundEventSchema = z.looseObject({
  sender: z.string(),
  webhook_id: z.string(),
  event_id: z.string(),
  type: z.string(),
  source: z.string(),
  subject: z.nullish(z.string()),
  time: z.nullish(z.string()),
  link: z.nullish(z.string()),
  received_at: z.string(),
  data: z.record(z.string(), z.unknown()),
})
export const inboundEventsSchema = z.array(inboundEventSchema)
export type InboundEvent = z.infer<typeof inboundEventSchema>
