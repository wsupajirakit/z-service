import { useEffect, useRef } from 'react'
import {
  CandlestickSeries, createChart, type IChartApi, type ISeriesApi, type UTCTimestamp,
} from 'lightweight-charts'
import { useTheme } from '../../hooks/useTheme.ts'
import type { Candle } from './candles.ts'
import { chartColors } from './chartTheme.ts'

export default function CandleChart({ candles }: { candles: Candle[] }) {
  const host = useRef<HTMLDivElement>(null)
  const chart = useRef<IChartApi | null>(null)
  const series = useRef<ISeriesApi<'Candlestick'> | null>(null)
  const theme = useTheme()

  useEffect(() => {
    if (!host.current) return
    // attributionLogo injects an inline <style>, which CSP style-src 'self' blocks.
    // The TradingView attribution is rendered by ChartPanel instead.
    const c = createChart(host.current, { autoSize: true, layout: { attributionLogo: false } })
    series.current = c.addSeries(CandlestickSeries)
    chart.current = c
    return () => {
      c.remove()
      chart.current = null
      series.current = null
    }
  }, [])

  useEffect(() => {
    series.current?.setData(candles.map((x) => ({ ...x, time: x.time as UTCTimestamp })))
    chart.current?.timeScale().fitContent()
  }, [candles])

  // Theme change = applyOptions on the existing chart, never a new chart.
  useEffect(() => {
    const col = chartColors()
    chart.current?.applyOptions({
      layout: { background: { color: col.bg }, textColor: col.fg },
      grid: { vertLines: { color: col.grid }, horzLines: { color: col.grid } },
    })
    series.current?.applyOptions({
      upColor: col.up, downColor: col.down, wickUpColor: col.up, wickDownColor: col.down,
      borderVisible: false,
    })
  }, [theme])

  return <div ref={host} className="h-80 w-full" data-testid="chart" />
}
