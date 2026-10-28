// Labels for the server's status enums (job mode/status/phase, round status/phase). Unknown
// values show as sent, so a new server state never renders blank.
import { m } from '../paraglide/messages.js'

const LABELS: Readonly<Record<string, Readonly<Record<string, () => string>>>> = {
  mode: {
    auto: m.enum_mode_auto,
    custom: m.enum_mode_custom,
  },
  phase: {
    building: m.enum_phase_building,
    cooldown: m.enum_phase_cooldown,
    fetching: m.enum_phase_fetching,
    idle: m.enum_phase_idle,
    saving: m.enum_phase_saving,
    screening: m.enum_phase_screening,
  },
  status: {
    done: m.enum_status_done,
    error: m.enum_status_error,
    idle: m.enum_status_idle,
    running: m.enum_status_running,
    stopped: m.enum_status_stopped,
  },
}

export type EnumKind = 'mode' | 'status' | 'phase'

export function enumLabel(kind: EnumKind, value: string | null | undefined): string {
  if (!value) return '-'
  const label = LABELS[kind]?.[value]
  return label ? label() : value
}
