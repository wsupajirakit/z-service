import { describe, expect, it } from 'vitest'
import { cleanExchange, cleanName, cleanSymbol, intInRange, positiveNumber } from './validate.ts'

describe('validate', () => {
  it('cleans symbols, exchanges and names', () => {
    expect(cleanSymbol(' brk.b ')).toBe('BRK.B')
    expect(cleanSymbol('a/b')).toBeNull()
    expect(cleanSymbol('')).toBeNull()
    expect(cleanExchange('nasdaq')).toBe('NASDAQ')
    expect(cleanExchange('NY SE')).toBeNull()
    expect(cleanName('  Tech ')).toBe('Tech')
    expect(cleanName('a/b')).toBeNull()
  })

  it('checks integer ranges and positive numbers', () => {
    expect(intInRange('-720', -720, 840)).toBe(-720)
    expect(intInRange('841', -720, 840)).toBeNull()
    expect(intInRange('1.5', 1, 100)).toBeNull()
    expect(intInRange('', 1, 100)).toBeNull()
    expect(positiveNumber('12.5')).toBe(12.5)
    expect(positiveNumber('0')).toBeNull()
  })
})
