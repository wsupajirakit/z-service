import { describe, expect, it } from 'vitest'
import { runWithCache } from '../../testing/mocks/actionHarness.ts'
import { renderPage } from '../../testing/mocks/renderPage.tsx'
import { MOCK_PASSWORD } from '../../testing/mocks/db.ts'
import {
  autoSkipQuery, changePasswordAction, destinationsQuery, saveAutoSkipAction,
  saveDestinationAction,
  saveTimezoneAction, saveTvModeAction, saveTvTokenAction, timezoneQuery, tvModeQuery,
  tvTokenQuery,
} from './api.ts'
import { SettingsPage } from './components/SettingsPage.tsx'
import { parseAutoSkip, parseTimezone, utcLabel } from './model.ts'

describe('settings', () => {
  it('formats and validates timezone and auto-skip input', () => {
    expect(utcLabel(420)).toBe('UTC+7')
    expect(utcLabel(-210)).toBe('UTC-3:30')
    expect(parseTimezone('840', '')).toEqual({ offset: 840, label: 'UTC+14' })
    expect(parseTimezone('-721', 'x')).toBeNull()
    expect(parseAutoSkip('100')).toBe(100)
    expect(parseAutoSkip('0')).toBeNull()
  })

  it('saves each setting and invalidates its query', async () => {
    const tz = await runWithCache(saveTimezoneAction, { offset: 60, label: 'Rome' },
      [timezoneQuery.queryKey])
    expect(tz.data).toEqual({ offset_minutes: 60, label: 'Rome' })
    expect(tz.invalidated).toHaveLength(1)
    const dest = await runWithCache(saveDestinationAction,
      { key: 'dest_gold_drive', on: true }, [destinationsQuery.queryKey])
    expect(dest.data.dest_gold_drive).toBe(true)
    const skip = await runWithCache(saveAutoSkipAction, 30, [autoSkipQuery.queryKey])
    expect(skip.data.minutes).toBe(30)
    const mode = await runWithCache(saveTvModeAction, 2,
      [tvModeQuery.queryKey, tvTokenQuery.queryKey])
    expect(mode.invalidated).toHaveLength(2)
    const token = await runWithCache(saveTvTokenAction, 'abc', [tvTokenQuery.queryKey])
    expect(token.data.status).toBe('active')
  })

  it('passes the server detail through on bad input', async () => {
    await expect(runWithCache(saveAutoSkipAction, 101, []))
      .rejects.toMatchObject({ detail: 'Minutes must be between 1 and 100' })
    await expect(runWithCache(saveTvTokenAction, 'expired', []))
      .rejects.toMatchObject({ detail: 'Token is already expired' })
  })

  it('renders every section from the cache', () => {
    const html = renderPage(<SettingsPage />, [
      [destinationsQuery.queryKey, { dest_stock_drive: true, dest_stock_telegram: false,
        dest_gold_drive: true, dest_gold_telegram: true }],
      [autoSkipQuery.queryKey, { minutes: 15 }],
      [tvModeQuery.queryKey, { mode: 1 }],
      [tvTokenQuery.queryKey, { status: 'active', expires_in_minutes: 12 }],
    ])
    expect(html).toContain('data-testid="tz-form"')
    expect(html).toContain('data-testid="dest-form"')
    expect(html).toContain('data-testid="tv-token-status"')
    expect(html).toContain('12')
    expect(html).toContain('type="password"')
    expect(html).toContain('data-testid="password-form"')
  })

  it('changes the password; a wrong current one is a 403, never a sign-out', async () => {
    const next = 'a much longer passphrase'
    await expect(runWithCache(changePasswordAction, { current: 'wrong', next }, []))
      .rejects.toMatchObject({ status: 403, code: 'auth.wrong_current_password' })
    await expect(runWithCache(changePasswordAction, { current: MOCK_PASSWORD, next: 'short' }, []))
      .rejects.toMatchObject({ code: 'auth.password_short', params: { min: 12 } })
    const done = await runWithCache(changePasswordAction, { current: MOCK_PASSWORD, next }, [])
    expect(done.data.status).toBe('ok')
  })
})
