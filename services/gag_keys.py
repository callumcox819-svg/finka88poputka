"""Совместимость: GAG → Aqua (Tori.fi / GOO Network)."""

from region import AQUA_DEFAULT_SERVICE, AQUA_DEFAULT_SERVICE as GAG_DEFAULT_SERVICE
from services.aqua_keys import (
    AQUA_PROFILE_ADDRESS_KEY as GAG_PROFILE_ADDRESS_KEY,
    AQUA_PROFILE_NAME_KEY as GAG_PROFILE_NAME_KEY,
    AQUA_PROFILE_TITLE_KEY as GAG_PROFILE_TITLE_KEY,
    AQUA_USER_API_KEY as GAG_API_KEY,
    aqua_service_for_html_dir as gag_service_for_html_dir,
    aqua_service_label as gag_service_label,
    get_user_aqua_api_key as get_user_gag_api_key,
    is_valid_aqua_service as is_valid_gag_service,
    normalize_aqua_service as normalize_gag_service,
)

GAG_SERVICE_KEY = "aqua_service"
GAG_DOMAIN_SLOT_KEY = "aqua_domain_unused"

GAG_SERVICE_CHOICES = (AQUA_DEFAULT_SERVICE,)


def gag_service_for_api(code: str | None) -> str:
    n = normalize_gag_service(code)
    if not n:
        raise ValueError(f"Unknown service: {code!r}")
    return n


def gag_service_matches(cur: str | None, choice: str) -> bool:
    return normalize_gag_service(cur) == normalize_gag_service(choice)


def gag_api_domain_param(slot: int | None) -> None:
    return None


def gag_generate_endpoint() -> str:
    from services.aqua_keys import aqua_api_base

    return f"{aqua_api_base()}/api/generate/single/parse"


def gag_send_email_endpoint() -> str:
    return ""


def gag_default_version() -> str:
    return "lk"


def resolve_gag_service(*, offer_link: str, user_setting: str | None) -> str | None:
    from region import AQUA_DEFAULT_SERVICE

    if (offer_link or "").lower().find("tori.fi") >= 0:
        return AQUA_DEFAULT_SERVICE
    n = normalize_gag_service(user_setting)
    return n or AQUA_DEFAULT_SERVICE


def parse_gag_domain_slot(raw: str | None) -> None:
    return None
