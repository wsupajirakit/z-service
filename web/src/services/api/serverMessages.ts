// Coded server texts (backend zservice/core/messages.py: status, progress, warnings, test
// logs) -> translated text. Explicit map, not m[key], so only the messages used are bundled.
// backend/tests/core/test_error_codes.py keeps the codes in sync with web/messages;
// serverMessages.test.ts checks every msg_* message has an entry here.
import { m } from '../../paraglide/messages.js'
import type { ErrorParams } from './error.ts'

type Render = (params: ErrorParams) => string

export const SERVER_MESSAGES: Readonly<Record<string, Render>> = {
  'earning.no_provider': () => m.msg_earning_no_provider(),
  'gold.not_running': () => m.msg_gold_not_running(),
  'gold.stop_sent': () => m.msg_gold_stop_sent(),
  'history.cleaned': (p) =>
    m.msg_history_cleaned({ deleted: p.deleted ?? '', hours: p.hours ?? '' }),
  'history.cleared': () => m.msg_history_cleared(),
  'radar.asof_ahead': (p) => m.msg_radar_asof_ahead({ asof: p.asof ?? '', hours: p.hours ?? '' }),
  'radar.data_old_days': (p) => m.msg_radar_data_old_days({ age: p.age ?? '', asof: p.asof ?? '' }),
  'radar.data_old_hours': (p) =>
    m.msg_radar_data_old_hours({ age: p.age ?? '', asof: p.asof ?? '' }),
  'radar.done': () => m.msg_radar_done(),
  'radar.done_pruned': (p) =>
    m.msg_radar_done_pruned({ count: p.count ?? '', keep: p.keep ?? '', stamps: p.stamps ?? '' }),
  'radar.failed': (p) => m.msg_radar_failed({ reason: p.reason ?? '' }),
  'radar.fetching_tf': (p) => m.msg_radar_fetching_tf({ tf: p.tf ?? '' }),
  'radar.formula_csv': () => m.msg_radar_formula_csv(),
  'radar.missing_1d_nodata': () => m.msg_radar_missing_1d_nodata(),
  'radar.missing_1d_unselected': () => m.msg_radar_missing_1d_unselected(),
  'radar.missing_1h_nodata': () => m.msg_radar_missing_1h_nodata(),
  'radar.missing_1h_unselected': () => m.msg_radar_missing_1h_unselected(),
  'radar.missing_1w_nodata': () => m.msg_radar_missing_1w_nodata(),
  'radar.missing_1w_unselected': () => m.msg_radar_missing_1w_unselected(),
  'radar.missing_4h_nodata': () => m.msg_radar_missing_4h_nodata(),
  'radar.missing_4h_unselected': () => m.msg_radar_missing_4h_unselected(),
  'radar.reused': () => m.msg_radar_reused(),
  'radar.saving': () => m.msg_radar_saving(),
  'radar.screening': (p) => m.msg_radar_screening({ tfs: p.tfs ?? '' }),
  'radar.short_without_4h': () => m.msg_radar_short_without_4h(),
  'radar.started': () => m.msg_radar_started(),
  'radar.tf_mixed': (p) => m.msg_radar_tf_mixed({ count: p.count ?? '', tf: p.tf ?? '' }),
  'radar.tf_older': (p) => m.msg_radar_tf_older({ hours: p.hours ?? '', tf: p.tf ?? '' }),
  'radar.thread_failed': () => m.msg_radar_thread_failed(),
  'tv.anonymous': () => m.msg_tv_anonymous(),
  'tv.cooldown_active': (p) => m.msg_tv_cooldown_active({ seconds: p.seconds ?? '' }),
  'tv.cooldown_none': () => m.msg_tv_cooldown_none(),
  'tv.login_failed_anonymous': (p) =>
    m.msg_tv_login_failed_anonymous({ username: p.username ?? '' }),
  'tv.login_failed_token_used': (p) =>
    m.msg_tv_login_failed_token_used({ username: p.username ?? '' }),
  'tv.login_ok': (p) => m.msg_tv_login_ok({ minutes: p.minutes ?? '', username: p.username ?? '' }),
  'tv.probe_empty': (p) =>
    m.msg_tv_probe_empty({ seconds: p.seconds ?? '', target: p.target ?? '' }),
  'tv.probe_error': (p) => m.msg_tv_probe_error({ error: p.error ?? '', target: p.target ?? '' }),
  'tv.probe_ok': (p) =>
    m.msg_tv_probe_ok({ bars: p.bars ?? '', seconds: p.seconds ?? '', target: p.target ?? '' }),
  'tv.probe_slow': (p) =>
    m.msg_tv_probe_slow({ bars: p.bars ?? '', seconds: p.seconds ?? '', target: p.target ?? '' }),
  'tv.probe_timeout': (p) =>
    m.msg_tv_probe_timeout({ seconds: p.seconds ?? '', target: p.target ?? '' }),
  'tv.token_expired': (p) => m.msg_tv_token_expired({ minutes: p.minutes ?? '' }),
  'tv.token_ok': (p) => m.msg_tv_token_ok({ minutes: p.minutes ?? '' }),
  'tv.token_unreadable': () => m.msg_tv_token_unreadable(),
  'tv.verdict_down': () => m.msg_tv_verdict_down(),
  'tv.verdict_ok': () => m.msg_tv_verdict_ok(),
  'tv.verdict_partial': () => m.msg_tv_verdict_partial(),
  'tv.verdict_slow': () => m.msg_tv_verdict_slow(),
}

/** A coded server text: `code` + `params` next to the server's own `text`. */
export type CodedText = { code?: string | null, params?: ErrorParams | null, text?: string | null }

/** The text in the selected language; the server's own text when this build lacks the code. */
export function serverText(msg: CodedText): string {
  const render = msg.code && Object.hasOwn(SERVER_MESSAGES, msg.code)
    ? SERVER_MESSAGES[msg.code] : undefined
  return render ? render(msg.params ?? {}) : (msg.text ?? '')
}
