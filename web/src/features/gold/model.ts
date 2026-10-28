// Pure gold-page logic.
import type { GoldJob } from './schemas.ts'

/** Only https Drive links are rendered as links; anything else stays text. */
export function safeExternalUrl(raw: string | null | undefined): string | null {
  if (!raw) return null
  try {
    const url = new URL(raw)
    return url.protocol === 'https:' ? url.toString() : null
  } catch {
    return null
  }
}

export const goldRunning = (job: GoldJob | undefined) => job?.status === 'running'
