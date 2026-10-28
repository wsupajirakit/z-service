import { queryOptions } from '@tanstack/react-query'
import { defineAction } from '../../services/api/action.ts'
import { apiGet, apiSend } from '../../services/api/client.ts'
import { timezoneQuery } from '../../services/api/common.ts'
import { appConfig } from '../../config/app.ts'
import type { DestinationKey } from './schemas.ts'
import {
  destinationsSchema, minutesSchema, passwordChangedSchema, timezoneSchema, tvModeSchema,
  tvTokenSchema,
} from './schemas.ts'

export { timezoneQuery }

const stale = appConfig.staleTime.static

export const destinationsQuery = queryOptions({
  queryKey: ['settings', 'destinations'],
  queryFn: ({ signal }) => apiGet('settings/destinations', destinationsSchema, { signal }),
  staleTime: stale,
})
export const autoSkipQuery = queryOptions({
  queryKey: ['settings', 'auto_skip_minutes'],
  queryFn: ({ signal }) => apiGet('settings/auto_skip_minutes', minutesSchema, { signal }),
  staleTime: stale,
})
export const tvModeQuery = queryOptions({
  queryKey: ['settings', 'tv_mode'],
  queryFn: ({ signal }) => apiGet('settings/tv_mode', tvModeSchema, { signal }),
  staleTime: stale,
})
export const tvTokenQuery = queryOptions({
  queryKey: ['settings', 'tv_token'],
  queryFn: ({ signal }) => apiGet('settings/tv_token', tvTokenSchema, { signal }),
  staleTime: appConfig.staleTime.list,
})

export const saveTimezoneAction = defineAction((v: { offset: number; label: string }) =>
  apiSend('post', 'settings/timezone', timezoneSchema, {
    body: { offset_minutes: v.offset, label: v.label },
  }), [timezoneQuery.queryKey])

/** Sends one flag at a time, as legacy does; the server answers with all four. */
export const saveDestinationAction = defineAction((v: { key: DestinationKey; on: boolean }) =>
  apiSend('post', 'settings/destinations', destinationsSchema, { body: { [v.key]: v.on } }),
[destinationsQuery.queryKey])

export const saveAutoSkipAction = defineAction((minutes: number) =>
  apiSend('post', 'settings/auto_skip_minutes', minutesSchema, { body: { minutes } }),
[autoSkipQuery.queryKey])

/** Changing the mode also drops the server's cached TradingView login. */
export const saveTvModeAction = defineAction((mode: number) =>
  apiSend('post', 'settings/tv_mode', tvModeSchema, { body: { mode } }),
[tvModeQuery.queryKey, tvTokenQuery.queryKey])

export const saveTvTokenAction = defineAction((token: string) =>
  apiSend('post', 'settings/tv_token', tvTokenSchema, { body: { token } }),
[tvTokenQuery.queryKey])

/** Every older session is revoked; the server answers with fresh session cookies. */
export const changePasswordAction = defineAction((v: { current: string; next: string }) =>
  apiSend('post', 'auth/password', passwordChangedSchema, {
    body: { current_password: v.current, new_password: v.next },
  }), [])
