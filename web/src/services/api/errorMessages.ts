// Server error codes (backend zservice/core/errors.py) -> translated text. An explicit map,
// not m[key]: dynamic lookup would pull every message into the first-load bundle.
// backend/tests/core/test_error_codes.py keeps codes and messages in sync with the server;
// errorMessages.test.ts checks every err_* message has an entry here.
import { m } from '../../paraglide/messages.js'
import { ApiError, type ErrorParams } from './error.ts'

type Render = (params: ErrorParams) => string

export const ERROR_MESSAGES: Readonly<Record<string, Render>> = {
  'events.bad_body': () => m.err_events_bad_body(),
  'events.bad_headers': () => m.err_events_bad_headers(),
  'events.bad_signature': () => m.err_events_bad_signature(),
  'events.not_cloudevent': () => m.err_events_not_cloudevent(),
  'events.stale': () => m.err_events_stale(),
  'events.too_large': () => m.err_events_too_large(),
  'events.unknown_sender': () => m.err_events_unknown_sender(),
  'ai.bad_response': () => m.err_ai_bad_response(),
  'ai.failed': (p) => m.err_ai_failed({ reason: p.reason ?? '' }),
  'ai.http_error': (p) => m.err_ai_http_error({ status: p.status ?? '' }),
  'ai.invalid_model': () => m.err_ai_invalid_model(),
  'ai.models_failed': () => m.err_ai_models_failed(),
  'ai.no_api_key': () => m.err_ai_no_api_key(),
  'ai.unavailable': () => m.err_ai_unavailable(),
  'auth.bad_credentials': () => m.err_auth_bad_credentials(),
  'auth.db_error': () => m.err_auth_db_error(),
  'auth.missing_fields': () => m.err_auth_missing_fields(),
  'auth.password_short': (p) => m.err_auth_password_short({ min: p.min ?? '' }),
  'auth.password_unchanged': () => m.err_auth_password_unchanged(),
  'auth.rate_limited': (p) => m.err_auth_rate_limited({ retry_after: p.retry_after ?? '' }),
  'auth.registration_closed': () => m.err_auth_registration_closed(),
  'auth.user_exists': () => m.err_auth_user_exists(),
  'auth.wrong_current_password': () => m.err_auth_wrong_current_password(),
  'drive.bad_id': () => m.err_drive_bad_id(),
  'drive.folder_required': () => m.err_drive_folder_required(),
  'drive.name_required': () => m.err_drive_name_required(),
  'drive.not_configured': () => m.err_drive_not_configured(),
  'drive.outside_root': () => m.err_drive_outside_root(),
  'drive.root_delete': () => m.err_drive_root_delete(),
  'exports.invalid_interval': (p) => m.err_exports_invalid_interval({ allowed: p.allowed ?? '' }),
  'gold.already_running': () => m.err_gold_already_running(),
  'gold_mode.invalid_exchange': (p) =>
    m.err_gold_mode_invalid_exchange({ allowed: p.allowed ?? '' }),
  'gold_mode.invalid_mode': (p) => m.err_gold_mode_invalid_mode({ allowed: p.allowed ?? '' }),
  'gold_mode.no_xau': (p) => m.err_gold_mode_no_xau({ exchange: p.exchange ?? '' }),
  'gold.price_failed': (p) => m.err_gold_price_failed({ reason: p.reason ?? '' }),
  'gold.unsupported_source': (p) => m.err_gold_unsupported_source({ allowed: p.allowed ?? '' }),
  'history.hours_range': (p) => m.err_history_hours_range({ max: p.max ?? '', min: p.min ?? '' }),
  'history.not_found': () => m.err_history_not_found(),
  // Sent by the body-size middleware (zservice/security/body_limit.py), not an ApiError.
  'http.too_large': (p) => m.err_http_too_large({ max: p.max ?? '' }),
  'jobs.already_running': () => m.err_jobs_already_running(),
  'jobs.no_symbols': () => m.err_jobs_no_symbols(),
  'jobs.no_timeframes': (p) => m.err_jobs_no_timeframes({ allowed: p.allowed ?? '' }),
  'jobs.server_list_empty': () => m.err_jobs_server_list_empty(),
  'lists.invalid_name': () => m.err_lists_invalid_name(),
  'lists.rename_failed': () => m.err_lists_rename_failed(),
  'market.fetch_failed': (p) => m.err_market_fetch_failed({ reason: p.reason ?? '' }),
  'market.invalid_interval': (p) => m.err_market_invalid_interval({ allowed: p.allowed ?? '' }),
  'market.no_data': () => m.err_market_no_data(),
  'radar.already_running': () => m.err_radar_already_running(),
  'radar.invalid_request': (p) => m.err_radar_invalid_request({ reason: p.reason ?? '' }),
  'radar.not_found': (p) => m.err_radar_not_found({ stamp: p.stamp ?? '' }),
  'settings.minutes_range': (p) =>
    m.err_settings_minutes_range({ max: p.max ?? '', min: p.min ?? '' }),
  'settings.offset_range': (p) =>
    m.err_settings_offset_range({ max: p.max ?? '', min: p.min ?? '' }),
  'tv.invalid_mode': () => m.err_tv_invalid_mode(),
  'tv.token_empty': () => m.err_tv_token_empty(),
  'tv.token_expired': () => m.err_tv_token_expired(),
}

/** Translated text for a server error code, or null when this build does not know it. */
export function codeMessage(code: string | null, params: ErrorParams): string | null {
  const render = code && Object.hasOwn(ERROR_MESSAGES, code) ? ERROR_MESSAGES[code] : undefined
  return render ? render(params) : null
}

/** Translated text for a known server error code, else the server detail with its status. */
export function errorText(error: unknown): string {
  if (!(error instanceof ApiError)) return m.error_generic()
  return codeMessage(error.code, error.params)
    ?? m.error_http({ status: error.status, detail: error.detail ?? '' })
}
