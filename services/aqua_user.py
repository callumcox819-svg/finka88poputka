"""Профиль Aqua и генерация ссылок GOO Network."""

from __future__ import annotations

import json
from dataclasses import dataclass

from services.aqua_keys import (
    AQUA_PROFILE_ADDRESS_KEY,
    AQUA_PROFILE_ID_KEY,
    AQUA_PROFILE_NAME_KEY,
    AQUA_PROFILE_PSEUDONYM_KEY,
    AQUA_PROFILE_TITLE_KEY,
    AQUA_USER_API_KEY,
    _LEGACY_GAG_ADDR,
    _LEGACY_GAG_NAME,
    _LEGACY_GAG_TITLE,
    aqua_service_label,
    get_aqua_profile_id,
    get_profile_field,
    get_team_aqua_api_key,
    get_user_aqua_api_key,
    is_valid_aqua_service,
    normalize_aqua_service,
    resolve_aqua_service,
)
from services.aqua_network import AquaError, generate_link_no_parse, generate_link_with_parse
from services.link_id import link_id_from_generated_url
from services.user_settings import get_setting, set_setting


@dataclass(frozen=True)
class AquaProfile:
    profile_id: str
    pseudonym: str
    title: str
    name: str
    address: str
    service: str
    service_label: str
    user_key_set: bool
    team_key_set: bool
    username: str
    telegram_id: int


class AquaNotConfiguredError(Exception):
    pass


async def load_aqua_profile(user_id: int, *, username: str = "", telegram_id: int = 0) -> AquaProfile:
    pid = await get_aqua_profile_id(user_id)
    pseudo = (await get_setting(user_id, AQUA_PROFILE_PSEUDONYM_KEY) or "").strip()
    title = await get_profile_field(user_id, AQUA_PROFILE_TITLE_KEY, _LEGACY_GAG_TITLE)
    name = await get_profile_field(user_id, AQUA_PROFILE_NAME_KEY, _LEGACY_GAG_NAME)
    addr = await get_profile_field(user_id, AQUA_PROFILE_ADDRESS_KEY, _LEGACY_GAG_ADDR)
    svc = normalize_aqua_service(
        await get_setting(user_id, "aqua_service") or await get_setting(user_id, "gag_service")
    )
    ukey = await get_user_aqua_api_key(user_id)
    tkey = await get_team_aqua_api_key(user_id)
    return AquaProfile(
        profile_id=pid,
        pseudonym=pseudo,
        title=title,
        name=name,
        address=addr,
        service=svc,
        service_label=aqua_service_label(svc),
        user_key_set=bool(ukey),
        team_key_set=bool(tkey),
        username=(username or "").strip(),
        telegram_id=int(telegram_id or user_id),
    )


def profile_ready(profile: AquaProfile) -> bool:
    return bool(profile.profile_id and profile.user_key_set and profile.team_key_set)


def format_aqua_profile_message(profile: AquaProfile) -> str:
    from utils.text_html import e

    pid = (profile.profile_id or "").strip()
    pid_set = bool(pid)
    pid_status = "🟢 задан" if pid_set else "🔴 не задан"
    un = profile.username or "—"
    if un and not un.startswith("@"):
        un = f"@{un}"
    user_key = "🟢 задан" if profile.user_key_set else "🔴 не задан"
    lines = [
        "🇫🇮 <b>Финляндия</b> › <b>Профиль</b> ⌄",
        "",
        f"Username: <code>{e(un)}</code>",
        f"User ID: <code>{profile.telegram_id}</code>",
        f"🆔 profileID: <b>{pid_status}</b>",
        f"🔑 User API: <b>{user_key}</b>",
    ]
    if pid_set:
        lines.append(f"   <code>{e(pid)}</code>")
    lines.extend(
        [
            "",
            "Для генерации ссылок: <b>profileID</b> + <b>User API key</b>.",
        ]
    )
    return "\n".join(lines)


def _fields_from_lead(lead: dict) -> dict[str, str | None]:
    title = (lead.get("item_title") or "").strip()
    price = (lead.get("item_price") or "").strip()
    link = (lead.get("item_link") or "").strip()
    photo = (lead.get("item_photo") or "").strip()
    if not title or not price:
        raw = (lead.get("raw_json") or "").strip()
        if raw:
            try:
                item = json.loads(raw)
                if isinstance(item, dict):
                    if not title:
                        title = str(
                            item.get("item_title")
                            or item.get("title")
                            or item.get("product_title")
                            or ""
                        ).strip()
                    if not price:
                        price = str(
                            item.get("item_price")
                            or item.get("price")
                            or item.get("offer_price")
                            or ""
                        ).strip()
                    if not link:
                        link = str(
                            item.get("item_link")
                            or item.get("link")
                            or item.get("url")
                            or ""
                        ).strip()
                    if not photo:
                        photo = str(
                            item.get("item_photo")
                            or item.get("photo")
                            or item.get("image")
                            or ""
                        ).strip()
            except json.JSONDecodeError:
                pass
    return {
        "title": title,
        "price": price or "0",
        "offer_link": link,
        "image": photo or None,
    }


async def generate_link_for_lead(user_id: int, lead: dict) -> str:
    fields = _fields_from_lead(lead)
    title = fields["title"] or ""
    if not title:
        raise AquaNotConfiguredError("У лида нет названия объявления.")
    return await generate_link_for_user(
        user_id,
        title=title,
        price=str(fields["price"] or "0"),
        offer_link=str(fields["offer_link"] or ""),
        image=fields["image"],
    )


async def generate_link_for_user(
    user_id: int,
    *,
    title: str,
    price: str,
    offer_link: str = "",
    image: str | None = None,
    balance_checker: bool = False,
) -> str:
    user_key = await get_user_aqua_api_key(user_id)
    team_key = await get_team_aqua_api_key(user_id)
    if not user_key:
        raise AquaNotConfiguredError(
            "Не задан User API key (⚙️ Настройки → 📋 Профиль → 🔑 User API key)."
        )
    if not team_key:
        raise AquaNotConfiguredError(
            "Не задан Team API key на сервере. Админ: переменная AQUA_TEAM_API_KEY в Railway."
        )

    profile = await load_aqua_profile(user_id, telegram_id=user_id)
    if not profile.profile_id:
        raise AquaNotConfiguredError(
            "Не указан profileID из Aqua (⚙️ Настройки → 📋 Профиль → 🆔 profileID)."
        )

    listing = (offer_link or "").strip()
    service = resolve_aqua_service(
        offer_link=listing,
        user_setting=profile.service,
    )
    if not listing.startswith("http") and not (title or "").strip():
        raise AquaNotConfiguredError(
            "Нет ссылки на объявление и названия товара для генерации."
        )
    try:
        if listing.startswith("http"):
            return await generate_link_with_parse(
                user_api_key=user_key,
                team_api_key=team_key,
                service=service,
                listing_url=listing,
                profile_id=profile.profile_id,
                balance_checker=balance_checker,
            )
        return await generate_link_no_parse(
            user_api_key=user_key,
            team_api_key=team_key,
            service=service,
            name=title.strip(),
            price=(price or "").strip() or "0",
            image=(image or "").strip() or "https://via.placeholder.com/300",
            profile_id=profile.profile_id,
            balance_checker=balance_checker,
        )
    except AquaError as exc:
        raise AquaNotConfiguredError(str(exc)) from exc


def ad_id_from_url(url: str) -> str | None:
    return link_id_from_generated_url(url)


async def migrate_legacy_gag_keys(user_id: int) -> None:
    """Один раз перенести gag_api_key → aqua_user_api_key."""
    old = (await get_setting(user_id, "gag_api_key") or "").strip()
    cur = (await get_setting(user_id, AQUA_USER_API_KEY) or "").strip()
    if old and not cur:
        await set_setting(user_id, AQUA_USER_API_KEY, old)


# Алиасы для старого кода (gag_link / incoming)
GagNotConfiguredError = AquaNotConfiguredError
load_gag_profile = load_aqua_profile
generate_link_for_lead_gag = generate_link_for_lead
