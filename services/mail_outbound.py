"""
Единая исходящая почта: рассылка, ответы, HTML.

Если у пользователя есть прокси в настройках — отправка только через SOCKS5.
Обычный режим: ротация по всем живым прокси.
Быстрая рассылка: один прокси + пачки / параллель.
"""

from __future__ import annotations

import os
from typing import Any

from config import Settings
from database import count_proxies, list_sendable_proxies
from services.encoding import TransferEncoding
from services.proxy_pool import (
    is_proxy_tunnel_error,
    mark_proxy_mailing_dead,
    pick_first_proxy,
    pick_next_proxy,
)
from services.html_spoof import prepare_html_outbound
from services.smtp_sender import EncodingName, send_batch_one, send_one

FAST_MAILING_PARALLEL = max(1, min(20, int(os.getenv("FAST_MAILING_PARALLEL", "8"))))
FAST_MAILING_BATCH = max(1, min(8, int(os.getenv("FAST_MAILING_BATCH", "8"))))


class NoLiveProxyError(RuntimeError):
    """Нет прокси в настройках или нет ни одного живого SOCKS5 для отправки."""


async def live_proxy_count(user_id: int) -> int:
    return len(await list_sendable_proxies(user_id))


async def user_has_proxies(user_id: int) -> bool:
    return (await count_proxies(user_id)) > 0


async def _require_proxy(user_id: int) -> list[dict]:
    uid = int(user_id)
    if not await user_has_proxies(uid):
        raise NoLiveProxyError(
            "Добавьте SOCKS5-прокси в 🌐 Прокси. "
            "Рассылка, ответы (пресеты/ручные) и HTML — только через прокси."
        )
    sendable = await list_sendable_proxies(uid)
    if not sendable:
        raise NoLiveProxyError(
            "В настройках есть прокси, но нет живых. "
            "Добавьте SOCKS5 или нажмите «Проверить прокси»."
        )
    return sendable


async def send_mail(
    settings: Settings,
    user_id: int,
    *,
    to_addr: str,
    subject: str,
    body: str,
    is_html: bool = False,
    transfer: TransferEncoding = TransferEncoding.AUTO,
    reply_to: str | None = None,
    account: dict[str, Any] | None = None,
    use_tls: bool | None = None,
    fast_mailing: bool = False,
) -> EncodingName:
    """Отправить одно письмо через SOCKS5."""
    uid = int(user_id)
    subject, body, from_display_name = await prepare_html_outbound(
        uid, subject=subject, body=body, is_html=is_html
    )
    await _require_proxy(uid)

    if fast_mailing:
        proxy = await pick_first_proxy(uid)
        if not proxy:
            raise NoLiveProxyError("Нет живого прокси для быстрой рассылки.")
        try:
            return await send_one(
                settings,
                to_addr=to_addr,
                subject=subject,
                body=body,
                is_html=is_html,
                transfer=transfer,
                reply_to=reply_to,
                account=account,
                from_display_name=from_display_name,
                use_tls=use_tls,
                proxy=proxy,
                parallel=True,
            )
        except Exception as exc:
            if proxy.get("id") and is_proxy_tunnel_error(exc):
                await mark_proxy_mailing_dead(uid, int(proxy["id"]), str(exc))
            raise

    last_exc: Exception | None = None
    sendable = await list_sendable_proxies(uid)
    for _ in range(len(sendable)):
        proxy = await pick_next_proxy(uid)
        if not proxy:
            break
        try:
            return await send_one(
                settings,
                to_addr=to_addr,
                subject=subject,
                body=body,
                is_html=is_html,
                transfer=transfer,
                reply_to=reply_to,
                account=account,
                from_display_name=from_display_name,
                use_tls=use_tls,
                proxy=proxy,
            )
        except Exception as exc:
            last_exc = exc
            if proxy.get("id") and is_proxy_tunnel_error(exc):
                await mark_proxy_mailing_dead(uid, int(proxy["id"]), str(exc))
            continue

    if last_exc is not None:
        raise last_exc
    raise NoLiveProxyError("Не удалось отправить через прокси.")


async def send_mail_batch(
    settings: Settings,
    user_id: int,
    *,
    items: list[tuple[str, str, str]],
    account: dict[str, Any],
    is_html: bool = False,
    transfer: TransferEncoding = TransferEncoding.AUTO,
    fast_mailing: bool = False,
    parallel: bool = False,
) -> list[EncodingName]:
    """
    Несколько писем с одного ящика за одно SMTP-подключение.
    items: (to_addr, subject, body)
    """
    uid = int(user_id)
    if not items:
        return []
    await _require_proxy(uid)

    prepared: list[tuple[str, str, str, bool]] = []
    for to_addr, subject, body in items:
        subj, b, _from_name = await prepare_html_outbound(
            uid, subject=subject, body=body, is_html=is_html
        )
        prepared.append((to_addr, subj, b, is_html))

    proxy = await pick_first_proxy(uid) if fast_mailing else await pick_next_proxy(uid)
    if not proxy:
        raise NoLiveProxyError("Нет живого прокси.")

    try:
        return await send_batch_one(
            settings,
            account=account,
            items=prepared,
            transfer=transfer,
            proxy=proxy,
            parallel=parallel or fast_mailing,
        )
    except Exception as exc:
        if proxy.get("id") and is_proxy_tunnel_error(exc):
            await mark_proxy_mailing_dead(uid, int(proxy["id"]), str(exc))
        raise
