// Endpoints used by the shell and by several pages (features must not import each other).
import { queryOptions, useQuery } from '@tanstack/react-query'
import * as z from 'zod/mini'
import { appConfig } from '../../config/app.ts'
import { apiGet } from './client.ts'
import { serverText } from './serverMessages.ts'

export const versionSchema = z.looseObject({
  version: z.string(),
  commit: z.nullish(z.string()),
  build_time: z.nullish(z.string()),
  symbols_count: z.optional(z.number()),
  build_symbols: z.optional(z.number()),
  missing_exchange: z.optional(z.array(z.string())),
  job_phase: z.nullish(z.string()),
  job_round: z.nullish(z.number()),
  job_total: z.nullish(z.number()),
  autostart: z.optional(z.boolean()),
})
export type VersionInfo = z.infer<typeof versionSchema>

export const timezoneSchema = z.looseObject({
  offset_minutes: z.number(),
  label: z.string(),
})
export type TimezoneSetting = z.infer<typeof timezoneSchema>

export const versionQuery = queryOptions({
  queryKey: ['version'],
  queryFn: ({ signal }) => apiGet('version', versionSchema, { signal }),
  staleTime: appConfig.staleTime.static,
})

export const timezoneQuery = queryOptions({
  queryKey: ['settings', 'timezone'],
  queryFn: ({ signal }) => apiGet('settings/timezone', timezoneSchema, { signal }),
  staleTime: appConfig.staleTime.static,
})

export const useVersion = () => useQuery(versionQuery)

/** Display timezone configured on the server; null until loaded. */
export function useTimezone(): TimezoneSetting | null {
  return useQuery(timezoneQuery).data ?? null
}

/** Typical write response: `{ status: 'ok' }`, sometimes with a message, and a `code` +
 * `params` for that message (zservice/core/messages.py) the UI translates. */
export const statusSchema = z.looseObject({
  status: z.optional(z.string()),
  message: z.optional(z.string()),
  detail: z.optional(z.string()),
  code: z.optional(z.string()),
  params: z.optional(z.record(z.string(), z.union([z.string(), z.number()]))),
})
export type StatusReply = z.infer<typeof statusSchema>

/** The reply's message in the selected language (server text when the code is unknown). */
export function replyText(reply: StatusReply, fallback: string): string {
  return serverText({ code: reply.code, params: reply.params, text: reply.message ?? reply.detail })
    || fallback
}
