// Pure radar-summary logic.
import { serverText } from '../../services/api/serverMessages.ts'
import type { RoundMeta, RoundStatus, TfStatus, TfEntry } from './schemas.ts'

export type TfRow = TfEntry & { tf: string }

/** Timeframes in the order the server sent them (the server owns the list). */
export function tfRows(status: TfStatus): TfRow[] {
  return Object.entries(status.timeframes).map(([tf, entry]) => ({ tf, ...entry }))
}

export function isRunning(status: RoundStatus | undefined): boolean {
  return status?.status === 'running'
}

/** The stamp to show: the one in the URL (it may be older than the list page), else the newest. */
export function pickStamp(stamps: string[], requested: string | null): string | null {
  return requested || stamps[0] || null
}

/** Translated warnings when the round carries codes; older rounds show their stored text. */
export function roundWarnings(round: RoundMeta): string[] {
  if (round.warnings_coded?.length) return round.warnings_coded.map(serverText)
  return (round.warnings ?? []).map((w) => (typeof w === 'string' ? w : JSON.stringify(w)))
}
