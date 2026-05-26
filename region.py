"""Региональные настройки бота (Финляндия / Tori.fi)."""

from __future__ import annotations

import os

BOT_DISPLAY_NAME = "Poputka88 Finland"
MARKETPLACE_NAME = "Tori.fi"

# Код service в GOO Network API (список сервисов: tori_fi)
AQUA_DEFAULT_SERVICE = (os.getenv("AQUA_DEFAULT_SERVICE", "tori_fi") or "tori_fi").strip()
GAG_DEFAULT_SERVICE = AQUA_DEFAULT_SERVICE  # совместимость

# Домен генерации ссылок (в Aqua — OLD)
AQUA_GENERATE_DOMAIN = (os.getenv("AQUA_GENERATE_DOMAIN", "OLD") or "OLD").strip()

HTML_DATA_DIR = "HTMLfi"

# Домены для ValidEmail при первом входе (приоритет отправки)
DEFAULT_VALIDATION_DOMAINS: tuple[str, ...] = (
    "elisa.fi",
    "gmail.com",
    "hotmail.com",
    "outlook.com",
    "yahoo.com",
    "icloud.com",
    "live.fi",
    "me.com",
)


def format_item_price(price: str) -> str:
    """Цена в письмах/HTML: EUR, если валюта не указана."""
    p = (price or "").strip()
    if not p:
        return ""
    upper = p.upper()
    if upper.startswith("EUR") or "€" in p:
        return p
    if any(upper.startswith(c) for c in ("CHF", "USD", "GBP", "NOK", "SEK", "DKK")):
        return p
    return f"{p} €"
