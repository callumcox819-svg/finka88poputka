"""SMTP через SOCKS5 (только smtplib — без глобального прокси для Postgres/asyncpg)."""

from __future__ import annotations

import asyncio
import logging
import os
import smtplib
import ssl
from contextlib import asynccontextmanager
from email.message import EmailMessage
from typing import Any

logger = logging.getLogger(__name__)

_lock = asyncio.Lock()


def clear_global_socks_proxy() -> None:
    """Сброс PySocks default proxy (не должен влиять на asyncpg)."""
    try:
        import socks

        socks.set_default_proxy()
    except Exception:
        pass


def _make_proxy_socket(proxy: dict[str, Any], *, timeout: int) -> Any:
    import socks

    host = (proxy.get("host") or "").strip()
    port = int(proxy.get("port") or 0)
    user = (proxy.get("username") or "").strip() or None
    pwd = (proxy.get("password") or "").strip() or None
    sock = socks.socksocket()
    sock.set_proxy(socks.SOCKS5, host, port, username=user, password=pwd, rdns=True)
    sock.settimeout(timeout)
    return sock


def _smtp_over_proxy(
    proxy: dict[str, Any],
    *,
    smtp_host: str,
    smtp_port: int,
    login: str,
    password: str,
    timeout: int,
) -> smtplib.SMTP:
    """SMTP-сессия через SOCKS5 без socks.set_default_proxy (иначе ломается PostgreSQL)."""
    clear_global_socks_proxy()
    sock = _make_proxy_socket(proxy, timeout=timeout)
    use_ssl = smtp_port == 465

    if use_ssl:
        sock.connect((smtp_host, smtp_port))
        ctx = ssl.create_default_context()
        ssock = ctx.wrap_socket(sock, server_hostname=smtp_host)
        srv = smtplib.SMTP_SSL(timeout=timeout)
        srv.sock = ssock
        try:
            srv.file = ssock.makefile("rb")
        except Exception:
            srv.file = None
        srv.ehlo_or_helo_if_needed()
        return srv

    sock.connect((smtp_host, smtp_port))
    srv = smtplib.SMTP(timeout=timeout)
    srv.sock = sock
    try:
        srv.file = sock.makefile("rb")
    except Exception:
        srv.file = None
    code, _ = srv.getreply()
    if code == -1:
        raise smtplib.SMTPConnectError(-1, "No SMTP banner")
    srv.ehlo_or_helo_if_needed()
    if smtp_port != 25:
        ctx = ssl.create_default_context()
        srv.starttls(context=ctx)
        srv.ehlo_or_helo_if_needed()
    return srv


@asynccontextmanager
async def proxy_smtp_context(proxy: dict[str, Any]):
    async with _lock:
        clear_global_socks_proxy()
        try:
            yield
        finally:
            clear_global_socks_proxy()


def send_message_sync(
    *,
    proxy: dict[str, Any],
    smtp_host: str,
    smtp_port: int,
    login: str,
    password: str,
    mail_from: str,
    to_addr: str,
    message: EmailMessage,
    timeout: int = 35,
) -> None:
    srv = _smtp_over_proxy(
        proxy,
        smtp_host=smtp_host,
        smtp_port=smtp_port,
        login=login,
        password=password,
        timeout=timeout,
    )
    try:
        if login and password:
            srv.login(login, password)
        srv.send_message(message)
    finally:
        try:
            srv.quit()
        except Exception:
            try:
                if srv.sock:
                    srv.sock.close()
            except Exception:
                pass


async def send_via_proxy(
    proxy: dict[str, Any],
    *,
    smtp_host: str,
    smtp_port: int,
    login: str,
    password: str,
    mail_from: str,
    to_addr: str,
    message: EmailMessage,
) -> None:
    timeout = max(20, min(60, int(os.getenv("MAIL_SMTP_TIMEOUT_SEC", "35"))))

    async def _run() -> None:
        async with proxy_smtp_context(proxy):
            await asyncio.to_thread(
                send_message_sync,
                proxy=proxy,
                smtp_host=smtp_host,
                smtp_port=smtp_port,
                login=login,
                password=password,
                mail_from=mail_from,
                to_addr=to_addr,
                message=message,
                timeout=timeout,
            )

    await asyncio.wait_for(_run(), timeout=timeout + 15)
