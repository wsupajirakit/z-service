"""Telegram notifications to the allowed chats (TELEGRAM_* settings below)."""

import urllib.parse
import urllib.request

from pydantic import SecretStr

from zservice.core.config import CommaList, ZsSettings, env_field, settings_getter


class TelegramSettings(ZsSettings):
    bot_token: SecretStr = env_field(
        "TELEGRAM_BOT_TOKEN", SecretStr(""), doc="Bot token; unset = notifications skipped."
    )
    allowed_chat_ids: CommaList = env_field(
        "TELEGRAM_ALLOWED_CHAT_IDS", (), doc="Comma-separated chat ids that get notifications."
    )


get_settings = settings_getter(TelegramSettings)


def send_telegram_message(text: str):
    cfg = get_settings()
    token = cfg.bot_token.get_secret_value()
    if not token or not cfg.allowed_chat_ids:
        print(
            "[telegram] TELEGRAM_BOT_TOKEN / TELEGRAM_ALLOWED_CHAT_IDS not set; "
            "skipping notification"
        )
        return
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    for chat_id in cfg.allowed_chat_ids:
        try:
            data = urllib.parse.urlencode(
                {
                    "chat_id": chat_id,
                    "text": text,
                    "parse_mode": "HTML",
                    "disable_web_page_preview": "true",
                }
            ).encode()
            request = urllib.request.Request(url, data=data)
            with urllib.request.urlopen(request, timeout=15) as resp:  # noqa: S310 — fixed https
                resp.read()
        except Exception as e:
            print(f"[telegram] failed to send to {chat_id}: {e}")
