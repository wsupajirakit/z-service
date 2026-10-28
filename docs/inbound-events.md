# Inbound events (any system → this service)

Other systems report results here as **CloudEvents 1.0** (structured JSON) delivered over
**Standard Webhooks** (signed POST). Nothing is written for one particular system: a
sender is a line of configuration.

## Receiving end

`POST /api/events/inbound/<sender name>` — public path, authenticated by the signature
(no session, no machine key).

| Check | Refused with |
|--|--|
| sender is configured | 404 `events.unknown_sender` |
| `webhook-id` and `webhook-timestamp` present | 400 `events.bad_headers` |
| timestamp within `ZS_EVENT_TOLERANCE_SECONDS` (default 300) | 401 `events.stale` |
| a valid `v1` (HMAC, sender `secret`) or `v1a` (Ed25519, sender `public_key`) signature over `<id>.<timestamp>.<body>` | 401 `events.bad_signature` |
| body is CloudEvents 1.0 (`specversion`, `id`, `source`, `type`) | 400 `events.not_cloudevent` |
| body ≤ `ZS_EVENT_MAX_BYTES` (256 KB) | 413 `events.too_large` |

Accepted → `204`. The same `webhook-id` from the same sender is stored once (a retry is
acknowledged again), so senders may retry freely. Events expire after `ZS_EVENT_KEEP_DAYS`.

## Reading

UI: *Inbound events* (sender, type, subject, time, and a link to the result in the system
that produced it, taken from `data.links.ui`). API: `GET /api/inbound-events?type=&sender=`
(signed-in users).

## Adding a sender

1. In the sending system, create a receiver (webhook / subscription) pointing at
   `https://<this host>/api/events/inbound/<name>` and copy its signing secret, or note its
   public key (Ed25519 senders publish one, e.g. `GET /v1/events/keys`).
2. Add the sender to `ZS_EVENT_SENDERS` (JSON list) and restart:
   `[{"name": "<name>", "secret": "whsec_…"}]` or `{"name": "<name>", "public_key": "whpk_…"}`
   (both may be given; either valid signature is enough).
3. Send a test from the sender (e.g. *Send test*); it appears in *Inbound events*.
