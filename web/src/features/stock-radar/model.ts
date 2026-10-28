// Pure stock-radar logic.
import type { RadarRun } from './schemas.ts'

/** Formulas may be names or objects; show a readable label either way. */
export function formulaLabel(formula: unknown): string {
  if (typeof formula === 'string') return formula
  if (formula && typeof formula === 'object' && 'name' in formula) {
    return String((formula as { name: unknown }).name)
  }
  return JSON.stringify(formula)
}

export function runSummary(run: RadarRun): { symbols: number; formulas: string[] } {
  return { symbols: run.symbols.length, formulas: run.formulas.map(formulaLabel) }
}
