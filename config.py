"""
Настройки бота Poputka88 Finland.

Секреты — в config_local.py (в .gitignore) или в Railway Variables.
"""

# ═══════════════════════════════════════════════════════════════════════════════
#  ВСТАВЬ СВОИ ЗНАЧЕНИЯ (или config_local.py / Variables на Railway)
# ═══════════════════════════════════════════════════════════════════════════════

BOT_TOKEN = ""  # токен нового бота от @BotFather

ADMIN_IDS = ""  # Telegram ID через запятую

VALIDEMAIL_API_KEY = ""
VALIDEMAIL_API_KEY_2 = ""
VALIDEMAIL_API_KEY_3 = ""
VALIDEMAIL_API_KEY_4 = ""
VALIDEMAIL_API_KEY_5 = ""

DEEPL_API_KEY = ""  # DeepL для кнопки «Перевести»

DATABASE_URL = ""  # PostgreSQL на Railway (пусто = SQLite data/bot.db локально)

# Team API key GOO Network — один на весь бот (Railway Variables), не у пользователей
AQUA_TEAM_API_KEY = ""

# ═══════════════════════════════════════════════════════════════════════════════

import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()

try:
    import config_local as _cl  # type: ignore[import-untyped]

    for _k in (
        "BOT_TOKEN",
        "ADMIN_IDS",
        "VALIDEMAIL_API_KEY",
        "VALIDEMAIL_API_KEY_2",
        "VALIDEMAIL_API_KEY_3",
        "VALIDEMAIL_API_KEY_4",
        "VALIDEMAIL_API_KEY_5",
        "DEEPL_API_KEY",
        "DATABASE_URL",
        "AQUA_TEAM_API_KEY",
    ):
        _v = getattr(_cl, _k, None)
        if _v:
            globals()[_k] = _v
except ImportError:
    pass


def _pick(hardcoded: str, env_name: str) -> str:
    if (hardcoded or "").strip():
        return hardcoded.strip()
    return os.getenv(env_name, "").strip()


def _admin_ids() -> frozenset[int]:
    raw = _pick(ADMIN_IDS, "ADMIN_IDS")
    ids = []
    for part in raw.replace(";", ",").split(","):
        part = part.strip()
        if part.isdigit():
            ids.append(int(part))
    return frozenset(ids)


def _validemail_api_keys() -> tuple[str, ...]:
    keys: list[str] = []
    seen: set[str] = set()
    for hard, env in (
        (VALIDEMAIL_API_KEY, "VALIDEMAIL_API_KEY"),
        (VALIDEMAIL_API_KEY_2, "VALIDEMAIL_API_KEY_2"),
        (VALIDEMAIL_API_KEY_3, "VALIDEMAIL_API_KEY_3"),
        (VALIDEMAIL_API_KEY_4, "VALIDEMAIL_API_KEY_4"),
        (VALIDEMAIL_API_KEY_5, "VALIDEMAIL_API_KEY_5"),
    ):
        k = _pick(hard, env)
        if k and k not in seen:
            seen.add(k)
            keys.append(k)
    extra = os.getenv("VALIDEMAIL_API_KEYS", "")
    for part in extra.replace(";", ",").split(","):
        k = part.strip()
        if k and k not in seen:
            seen.add(k)
            keys.append(k)
    return tuple(keys)


@dataclass(frozen=True)
class Settings:
    bot_token: str
    admin_ids: frozenset[int]
    smtp_host: str
    smtp_port: int
    smtp_user: str
    smtp_password: str
    smtp_from: str
    smtp_use_tls: bool
    send_delay_sec: float
    max_recipients: int
    validemail_api_keys: tuple[str, ...]
    validemail_url: str
    validemail_timeout: int
    validemail_concurrency: int
    goo_api_base: str
    aqua_generate_domain: str


def load_settings() -> Settings:
    token = _pick(BOT_TOKEN, "BOT_TOKEN")
    if not token:
        raise RuntimeError(
            "BOT_TOKEN пустой. Вставь токен в config.py / config_local.py "
            "или задай BOT_TOKEN на сервере."
        )

    keys = _validemail_api_keys()

    return Settings(
        bot_token=token,
        admin_ids=_admin_ids(),
        smtp_host=os.getenv("SMTP_HOST", "localhost").strip(),
        smtp_port=int(os.getenv("SMTP_PORT", "587")),
        smtp_user=os.getenv("SMTP_USER", "").strip(),
        smtp_password=os.getenv("SMTP_PASSWORD", ""),
        smtp_from=os.getenv("SMTP_FROM", os.getenv("SMTP_USER", "")).strip(),
        smtp_use_tls=os.getenv("SMTP_USE_TLS", "true").lower() in ("1", "true", "yes"),
        send_delay_sec=float(os.getenv("SEND_DELAY_SEC", "2")),
        max_recipients=int(os.getenv("MAX_RECIPIENTS_PER_CAMPAIGN", "5000")),
        validemail_api_keys=keys,
        validemail_url=os.getenv(
            "VALIDEMAIL_URL", "https://validemail.co/api/v1/validate"
        ).strip(),
        validemail_timeout=int(os.getenv("VALIDEMAIL_TIMEOUT", "8")),
        validemail_concurrency=int(os.getenv("VALIDEMAIL_CONCURRENCY", "12")),
        goo_api_base=os.getenv("GOO_API_BASE", "https://api.goo.network").strip(),
        aqua_generate_domain=os.getenv("AQUA_GENERATE_DOMAIN", "OLD").strip() or "OLD",
    )
