#!/usr/bin/env bash
# zsvc_curl.sh — curl wrapper for shell scripts: key from env/Keychain, header only, TLS verified.
#   source "$ZSERVICE_REPO/tools/zsvc_curl.sh"   # ZSERVICE_REPO = the z-service checkout
#   zsvc_curl -m 15 "$ZS_BASE_URL/api/automate/status"
#   zsvc_curl -m 1500 -o out.zip -w "%{http_code}" "$ZS_BASE_URL/api/export_zip?all=true"
# Same lookup as zsvc_client.py: ZS_API_KEY, else Keychain service z-service / account ${ZS_KEY_ACCOUNT:-home}.
# Never add -k: the server certificate is valid and must be verified.

: "${ZS_BASE_URL:=https://z-service.duckdns.org}"
export ZS_BASE_URL

_zsvc_key() {
  if [ -n "${ZS_API_KEY:-}" ]; then printf '%s' "$ZS_API_KEY"; return; fi
  security find-generic-password -s "${ZS_KEYCHAIN_SERVICE:-z-service}" -a "${ZS_KEY_ACCOUNT:-home}" -w 2>/dev/null
}

zsvc_curl() {
  local key; key="$(_zsvc_key)"
  case "$key" in
    zsk_*) ;;
    *) echo "zsvc_curl: no zsk_ key (set ZS_API_KEY or run tools/manage_keys.py new ...)" >&2; return 2 ;;
  esac
  # The header goes through a file descriptor so the key is not in curl's argv (visible in ps).
  curl -sS --proto '=https' -H @<(printf 'Authorization: Bearer %s\n' "$key") "$@"
}
