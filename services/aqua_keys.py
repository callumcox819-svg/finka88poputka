"""Aqua / GOO Network API (Финляндия: Tori.fi, Posti.fi)."""

from __future__ import annotations

import os

from region import AQUA_DEFAULT_SERVICE, AQUA_GENERATE_DOMAIN
from services.user_settings import get_setting

AQUA_USER_API_KEY = "aqua_user_api_key"
AQUA_TEAM_API_KEY = "aqua_team_api_key"
AQUA_PROFILE_ID_KEY = "aqua_profile_id"
AQUA_PROFILE_PSEUDONYM_KEY = "aqua_profile_pseudonym"
AQUA_PROFILE_TITLE_KEY = "aqua_profile_title"
AQUA_PROFILE_NAME_KEY = "aqua_profile_name"
AQUA_PROFILE_ADDRESS_KEY = "aqua_profile_address"
AQUA_SERVICE_KEY = "aqua_service"
GAG_SERVICE_KEY = AQUA_SERVICE_KEY

AQUA_SERVICE_CHOICES = ("tori_fi", "posti_fi")

_SERVICE_ALIASES: dict[str, str] = {
    "tori_fi": "tori_fi",
    "tori.fi": "tori_fi",
    "tori": "tori_fi",
    "posti_fi": "posti_fi",
    "posti.fi": "posti_fi",
    "posti": "posti_fi",
}

# Старые ключи GAG (миграция настроек без потери данных)
_LEGACY_GAG_API_KEY = "gag_api_key"
_LEGACY_GAG_TITLE = "gag_profile_title"
_LEGACY_GAG_NAME = "gag_profile_name"
_LEGACY_GAG_ADDR = "gag_profile_address"
_LEGACY_GAG_SERVICE = "gag_service"


def aqua_generate_domain() -> str:
    return (os.getenv("AQUA_GENERATE_DOMAIN", AQUA_GENERATE_DOMAIN) or AQUA_GENERATE_DOMAIN).strip()


def aqua_api_base() -> str:
    """Финляндия (команда AQUA): legacy-хост api-old.goo.network (см. Finkabot / docs.goo.network)."""
    return (
        os.getenv("GOO_API_BASE", "https://api-old.goo.network")
        or "https://api-old.goo.network"
    ).rstrip("/")


def aqua_api_host() -> str:
    from urllib.parse import urlparse

    try:
        return urlparse(aqua_api_base()).netloc or "api-old.goo.network"
    except Exception:
        return "api-old.goo.network"


def normalize_aqua_api_key(value: str | None) -> str:
    """Ключ без пробелов; убрать префикс Apikey, если вставили из заголовка."""
    from utils.secrets import clean_secret

    v = clean_secret(value)
    if not v:
        return ""
    low = v.lower()
    if low.startswith("apikey"):
        v = v[6:].lstrip(":").strip()
    return v


def normalize_aqua_service(code: str | None) -> str | None:
    s = (code or "").strip().lower()
    if not s:
        return None
    return _SERVICE_ALIASES.get(s)


def is_valid_aqua_service(code: str | None) -> bool:
    return normalize_aqua_service(code) is not None


def aqua_service_label(code: str | None) -> str:
    n = normalize_aqua_service(code) or (code or "").strip()
    return {
        "tori_fi": "Tori.fi",
        "posti_fi": "Posti.fi",
    }.get(n, n or "—")


def aqua_service_matches(cur: str | None, choice: str) -> bool:
    return normalize_aqua_service(cur) == normalize_aqua_service(choice)


def aqua_service_for_html_dir(code: str | None) -> str:
    return normalize_aqua_service(code) or ""


def aqua_service_from_link(link: str) -> str | None:
    l = (link or "").lower()
    if "posti.fi" in l:
        return "posti_fi"
    if "tori.fi" in l:
        return "tori_fi"
    return None


def resolve_aqua_service(*, offer_link: str = "", user_setting: str | None = None) -> str:
    """Сервис Aqua: сначала выбор в 📋 Профиле, иначе tori/posti в URL, иначе дефолт региона."""
    chosen = normalize_aqua_service(user_setting)
    if chosen:
        return chosen
    from_link = aqua_service_from_link(offer_link)
    if from_link:
        return from_link
    return AQUA_DEFAULT_SERVICE


async def resolve_aqua_service_for_mail(user_id: int, mail: dict) -> str:
    """Сервис для HTML: профиль → метка письма → ссылка лида → дефолт."""
    raw = (await get_setting(user_id, AQUA_SERVICE_KEY) or "").strip()
    if not raw:
        raw = (await get_setting(user_id, _LEGACY_GAG_SERVICE) or "").strip()
    chosen = normalize_aqua_service(raw)
    if chosen:
        return chosen

    label = normalize_aqua_service((mail.get("service_label") or "").strip())
    if label:
        return label

    lead_id = int(mail.get("lead_id") or 0)
    if lead_id > 0:
        from database import get_validated_lead_by_id

        lead = await get_validated_lead_by_id(user_id, lead_id)
        if lead:
            from_link = aqua_service_from_link(str(lead.get("item_link") or ""))
            if from_link:
                return from_link

    return AQUA_DEFAULT_SERVICE


async def get_user_aqua_api_key(user_id: int) -> str:
    k = normalize_aqua_api_key(await get_setting(user_id, AQUA_USER_API_KEY))
    if k:
        return k
    return normalize_aqua_api_key(await get_setting(user_id, _LEGACY_GAG_API_KEY))


def global_team_aqua_api_key() -> str:
    """Team key задаётся один раз на Railway (AQUA_TEAM_API_KEY), не у пользователей."""
    v = (os.getenv("AQUA_TEAM_API_KEY") or os.getenv("TEAM_API_KEY") or "").strip()
    if v:
        return normalize_aqua_api_key(v)
    try:
        import config

        return normalize_aqua_api_key(getattr(config, "AQUA_TEAM_API_KEY", "") or "")
    except Exception:
        return ""


async def get_team_aqua_api_key(user_id: int) -> str:
    g = global_team_aqua_api_key()
    if g:
        return g
    return normalize_aqua_api_key(await get_setting(user_id, AQUA_TEAM_API_KEY))


async def get_aqua_profile_id(user_id: int) -> str:
    return (await get_setting(user_id, AQUA_PROFILE_ID_KEY) or "").strip()


async def get_profile_field(user_id: int, new_key: str, legacy_key: str) -> str:
    v = (await get_setting(user_id, new_key) or "").strip()
    if v:
        return v
    return (await get_setting(user_id, legacy_key) or "").strip()
