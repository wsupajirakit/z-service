import { Suspense, lazy } from 'react'
import { m } from '../../paraglide/messages.js'
import type { Candle } from './candles.ts'

// lightweight-charts loads only when this panel renders.
const CandleChart = lazy(() => import('./CandleChart.tsx'))

export function ChartPanel({ title, candles }: { title: string; candles: Candle[] }) {
  return (
    <section className="space-y-2">
      <h3 className="text-sm font-semibold">{title}</h3>
      <div className="overflow-hidden rounded-lg border bg-card">
        <Suspense fallback={<div className="h-80 animate-pulse bg-muted" />}>
          <CandleChart candles={candles} />
        </Suspense>
      </div>
      <p className="text-xs text-muted-foreground">
        <a className="hover:underline" href="https://www.tradingview.com/"
          rel="noopener noreferrer" target="_blank">
          {m.chart_attribution()}
        </a>
      </p>
    </section>
  )
}
