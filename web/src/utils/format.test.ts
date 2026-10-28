import { describe, expect, it } from 'vitest'
import { cellText, formatDateTime, formatNumber } from './format.ts'

const zone = { offset_minutes: 420, label: 'UTC+7' }

describe('formatDateTime', () => {
  it('shows the wall clock of the server timezone, not the browser one', () => {
    const text = formatDateTime('2026-10-23T09:30:00Z', 'en', zone)
    expect(text).toContain('4:30')
    expect(text).toContain('(UTC+7)')
  })
  it('formats per locale', () => {
    expect(formatDateTime('2026-10-23T09:30:00Z', 'it', zone)).toContain('ott')
    expect(formatDateTime('2026-10-23T09:30:00Z', 'th', zone)).toContain('ต.ค.')
  })
  it('passes unparsable text through', () => {
    expect(formatDateTime('soon', 'en', zone)).toBe('soon')
    expect(formatDateTime(null, 'en', zone)).toBe('')
  })
})

describe('formatNumber / cellText', () => {
  it('uses the locale separators and accepts numeric strings', () => {
    expect(formatNumber(1234.5, 'en')).toBe('1,234.5')
    expect(formatNumber('12345.5', 'it')).toBe('12.345,5')
    expect(formatNumber('n/a', 'en')).toBe('n/a')
  })
  it('renders objects as JSON text', () => {
    expect(cellText({ a: 1 }, 'en')).toBe('{"a":1}')
    expect(cellText(null, 'en')).toBe('')
  })
})
