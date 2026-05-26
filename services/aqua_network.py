"""HTTP-клиент GOO Network (Aqua) — генерация ссылок."""

from __future__ import annotations

import asyncio
import json
from typing import Any

import aiohttp
from aiohttp import ClientError

from services.aqua_keys import aqua_api_base, aqua_generate_domain


class AquaError(Exception):
    pass


def _is_transient(err: BaseException) -> bool:
    if isinstance(err, (asyncio.TimeoutError, ClientError, ConnectionResetError, OSError)):
        return True
    msg = str(err).lower()
    return "connection" in msg or "disconnected" in msg


def _headers(*, user_api_key: str, team_api_key: str) -> dict[str, str]:
    return {
        "Authorization": f"Apikey {user_api_key.strip()}",
        "Host": "api.goo.network",
        "X-Team-Key": team_api_key.strip(),
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
                    if resp.status != 200:
                        raise AquaError(f"HTTP {resp.status}: {text[:400]}")
                    try:
                        data = json.loads(text)
                    except json.JSONDecodeError:
                        raise AquaError(f"Bad JSON: {text[:300]}")
            if not isinstance(data, dict):
                raise AquaError(f"Unexpected response: {str(data)[:300]}")
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
    domain: str | None = None,
    balance_checker: bool = False,
) -> str:
    body: dict[str, Any] = {
        "service": service,
        "url": listing_url.strip(),
        "profileID": profile_id.strip(),
        "isNeedBalanceChecker": bool(balance_checker),
        "domain": (domain or aqua_generate_domain()).strip(),
    }
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
    domain: str | None = None,
    balance_checker: bool = False,
) -> str:
    body: dict[str, Any] = {
        "service": service,
        "name": (name or "").strip() or "Item",
        "price": price,
        "image": (image or "").strip() or "https://via.placeholder.com/300",
        "profileID": profile_id.strip(),
        "isNeedBalanceChecker": bool(balance_checker),
        "domain": (domain or aqua_generate_domain()).strip(),
    }
    data = await _post_json(
        "/api/generate/single/no-parse",
        body,
        user_api_key=user_api_key,
        team_api_key=team_api_key,
    )
    return _extract_link(data)
