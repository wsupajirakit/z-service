import { describe, expect, it } from 'vitest'
import { filterSymbols, listSymbols, toTargets, toggle } from './symbols.ts'

const all = [
  { symbol: 'AAPL', name: 'Apple', exchange: 'NASDAQ' },
  { symbol: 'KO', name: 'Coca-Cola', exchange: 'NYSE' },
]

describe('symbol helpers', () => {
  it('filters by symbol or name, maps lists and exchanges', () => {
    expect(filterSymbols(all, 'cola', 10).map((s) => s.symbol)).toEqual(['KO'])
    expect(filterSymbols(all, '', 1)).toHaveLength(1)
    expect(listSymbols({ L: [{ symbol: 'KO' }, { symbol: 'AAPL' }, { symbol: 'KO' }] }, 'L'))
      .toEqual(['AAPL', 'KO'])
    expect(toTargets(['KO', 'ZZZ'], all)).toEqual({
      targets: [{ symbol: 'KO', exchange: 'NYSE' }], missing: ['ZZZ'],
    })
    expect(toggle(['A'], 'B', true)).toEqual(['A', 'B'])
    expect(toggle(['A', 'B'], 'A', false)).toEqual(['B'])
  })
})
