"""HTTP-клиент GOO Network (AQUA) — генерация ссылок (Финляндия → api-old)."""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

import aiohttp
from aiohttp import ClientError

from services.aqua_keys import aqua_api_base, aqua_api_host, normalize_aqua_api_key

logger = logging.getLogger(__name__)


class AquaError(Exception):
    pass


def _is_transient(err: BaseException) -> bool:
    if isinstance(err, (asyncio.TimeoutError, ClientError, ConnectionResetError, OSError)):
        return True
    msg = str(err).lower()
    return "connection" in msg or "disconnected" in msg


def _headers(*, user_api_key: str, team_api_key: str) -> dict[str, str]:
    user_key = normalize_aqua_api_key(user_api_key)
    team_key = normalize_aqua_api_key(team_api_key)
    if not user_key:
        raise AquaError("Не задан User API key (📋 Профиль → 🔑 User API key).")
    if not team_key:
        raise AquaError(
            "Не задан Team API key на сервере (Railway → AQUA_TEAM_API_KEY, «Ключ команды» в Aqua)."
        )
    return {
        "Authorization": f"Apikey {user_key}",
        "Host": aqua_api_host(),
        "X-Team-Key": team_key,
        "Content-Type": "application/json",
    }


def _extract_link(data: dict[str, Any]) -> str:
    if not data.get("status"):
        raise AquaError(str(data.get("message") or data)[:400])
    msg = data.get("message")
    if isinstance(msg, str) and msg.strip().startswith("http"):
        return msg.strip()
    if isinstance(msg, dict):
        link = (msg.get("link") or "").strip()
        if link:
            return link
    link = (data.get("url") or "").strip()
    if isinstance(link, str) and link.startswith("http"):
        return link
    raise AquaError(f"No link in response: {str(data)[:400]}")


async def _post_json(
    path: str,
    body: dict[str, Any],
    *,
    user_api_key: str,
    team_api_key: str,
    timeout_sec: float = 30.0,
) -> dict[str, Any]:
    url = f"{aqua_api_base()}{path}"
    timeout = aiohttp.ClientTimeout(total=timeout_sec)
    last: BaseException | None = None

    for attempt in range(3):
        try:
            connector = aiohttp.TCPConnector(force_close=True, enable_cleanup_closed=True)
            async with aiohttp.ClientSession(timeout=timeout, connector=connector) as session:
                async with session.post(
                    url,
                    json=body,
                    headers=_headers(user_api_key=user_api_key, team_api_key=team_api_key),
                ) as resp:
                    text = await resp.text()
                    try:
                        data = json.loads(text)
                    except json.JSONDecodeError:
                        data = None
                    if resp.status != 200:
                        msg = ""
                        if isinstance(data, dict):
                            msg = str(data.get("message") or data.get("error") or "")
                        if resp.status in (401, 403):
                            logger.warning(
                                "AQUA auth failed %s %s host=%s",
                                resp.status,
                                path,
                                aqua_api_host(),
                            )
                            raise AquaError(
                                f"HTTP {resp.status}: {msg or 'invalid credentials'}\n\n"
                                "Проверь:\n"
                                "• Личный ключ: Aqua → Инструменты → Генерация ссылок → "
                                "поле <b>Ключ</b> (не «Ключ команды») → 📋 Профиль → User API key\n"
                                "• Команда: Railway → <code>AQUA_TEAM_API_KEY</code> "
                                "(«Ключ команды» в Aqua)\n"
                                f"• API: <code>{aqua_api_base()}</code>"
                            )
                        raise AquaError(f"HTTP {resp.status}: {msg or text[:400]}")
            if not isinstance(data, dict):
                raise AquaError(f"Bad JSON: {text[:300]}")
            return data
        except AquaError:
            raise
        except Exception as exc:
            last = exc
            if attempt + 1 >= 3 or not _is_transient(exc):
                raise
            await asyncio.sleep(1.5 * (attempt + 1))
    if last:
        raise last
    raise AquaError("Aqua request failed")


async def generate_link_with_parse(
    *,
    user_api_key: str,
    team_api_key: str,
    service: str,
    listing_url: str,
    profile_id: str,
    image: str | None = None,
    balance_checker: bool = False,
) -> str:
    """POST /api/generate/single/parse — как в docs.goo.network / Finkabot (без domain)."""
    body: dict[str, Any] = {
        "service": service,
        "url": listing_url.strip(),
        "profileID": profile_id.strip(),
        "isNeedBalanceChecker": bool(balance_checker),
    }
    img = (image or "").strip()
    if img.lower().startswith(("http://", "https://")):
        body["image"] = img
    data = await _post_json(
        "/api/generate/single/parse",
        body,
        user_api_key=user_api_key,
        team_api_key=team_api_key,
    )
    return _extract_link(data)


async def generate_link_no_parse(
    *,
    user_api_key: str,
    team_api_key: str,
    service: str,
    name: str,
    price: str | int | float,
    image: str,
    profile_id: str,
    balance_checker: bool = False,
) -> str:
    """POST /api/generate/single/no-parse."""
    body: dict[str, Any] = {
        "service": service,
        "name": (name or "").strip() or "Item",
        "price": price,
        "image": (image or "").strip() or "https://via.placeholder.com/300",
        "profileID": profile_id.strip(),
        "isNeedBalanceChecker": bool(balance_checker),
    }
    data = await _post_json(
        "/api/generate/single/no-parse",
        body,
        user_api_key=user_api_key,
        team_api_key=team_api_key,
    )
    return _extract_link(data)
