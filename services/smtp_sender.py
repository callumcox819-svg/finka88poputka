"""SMTP send with correct MIME encoding.

Для бота используйте services.mail_outbound.send_mail — там политика прокси.
"""

from __future__ import annotations

import ssl
from email.message import EmailMessage
from email.policy import SMTP
from typing import Any, Literal

import aiosmtplib

from config import Settings
from services.encoding import TransferEncoding, resolve_encoding
from services.proxy_smtp import send_batch_via_proxy, send_via_proxy
from services.subject_offer import sanitize_email_subject

EncodingName = Literal["7bit", "quoted-printable", "base64"]


def build_message(
    *,
    mail_from: str,
    to_addr: str,
    subject: str,
    body: str,
    is_html: bool,
    encoding: EncodingName,
    reply_to: str | None = None,
) -> EmailMessage:
    msg = EmailMessage(policy=SMTP)
    msg["From"] = sanitize_email_subject(mail_from)
    msg["To"] = sanitize_email_subject(to_addr)
    msg["Subject"] = sanitize_email_subject(subject)
    if reply_to:
        msg["Reply-To"] = sanitize_email_subject(reply_to)

    subtype = "html" if is_html else "plain"
    charset = "us-ascii" if encoding == "7bit" else "utf-8"

    if encoding == "7bit":
        msg.set_content(body, subtype=subtype, charset=charset, cte="7bit")
    elif encoding == "quoted-printable":
        msg.set_content(body, subtype=subtype, charset=charset, cte="quoted-printable")
    else:
        msg.set_content(body, subtype=subtype, charset=charset, cte="base64")

    return msg


def format_from_header(account: dict[str, Any]) -> str:
    name = sanitize_email_subject(account.get("sender_name") or "")
    email = (account.get("email") or "").strip()
    if name:
        return f'"{name}" <{email}>'
    return email


def format_from_with_name(email: str, display_name: str | None) -> str:
    name = sanitize_email_subject(display_name or "")
    email = (email or "").strip()
    if name:
        return f'"{name}" <{email}>'
    return email


async def send_one(
    settings: Settings,
    *,
    to_addr: str,
    subject: str,
    body: str,
    is_html: bool,
    transfer: TransferEncoding = TransferEncoding.AUTO,
    reply_to: str | None = None,
    account: dict[str, Any] | None = None,
    from_display_name: str | None = None,
    use_tls: bool | None = None,
    proxy: dict[str, Any] | None = None,
    parallel: bool = False,
) -> EncodingName:
    enc = resolve_encoding(transfer, body, is_html=is_html)

    if account:
        if from_display_name:
            mail_from = format_from_with_name(account["email"], from_display_name)
        else:
            mail_from = format_from_header(account)
        host = account["smtp_host"]
        port = int(account["smtp_port"])
        user = account["email"]
        password = account["password"]
        tls_default = port != 25
    else:
        mail_from = settings.smtp_from
        host = settings.smtp_host
        port = settings.smtp_port
        user = settings.smtp_user
        password = settings.smtp_password
        tls_default = settings.smtp_use_tls

    message = build_message(
        mail_from=mail_from,
        to_addr=to_addr,
        subject=subject,
        body=body,
        is_html=is_html,
        encoding=enc,
        reply_to=reply_to,
    )

    if proxy:
        await send_via_proxy(
            proxy,
            smtp_host=host,
            smtp_port=port,
            login=user or "",
            password=password or "",
            mail_from=mail_from,
            to_addr=to_addr,
            message=message,
            parallel=parallel,
        )
        return enc

    tls_on = tls_default if use_tls is None else use_tls
    tls_ctx = ssl.create_default_context()
    use_ssl = tls_on and port == 465

    await aiosmtplib.send(
        message,
        hostname=host,
        port=port,
        username=user or None,
        password=password or None,
        start_tls=tls_on and not use_ssl,
        use_tls=use_ssl,
        tls_context=tls_ctx,
    )
    return enc


async def send_batch_one(
    settings: Settings,
    *,
    account: dict[str, Any],
    items: list[tuple[str, str, str, bool]],
    transfer: TransferEncoding = TransferEncoding.AUTO,
    from_display_name: str | None = None,
    proxy: dict[str, Any] | None = None,
    parallel: bool = False,
) -> list[EncodingName]:
    """
    items: (to_addr, subject, body, is_html) — одно SMTP-подключение.
    """
    del settings
    if not items or not proxy:
        return []

    if from_display_name:
        mail_from = format_from_with_name(account["email"], from_display_name)
    else:
        mail_from = format_from_header(account)

    host = account["smtp_host"]
    port = int(account["smtp_port"])
    user = account["email"]
    password = account["password"]

    messages: list[EmailMessage] = []
    encodings: list[EncodingName] = []
    for to_addr, subject, body, is_html in items:
        enc = resolve_encoding(transfer, body, is_html=is_html)
        encodings.append(enc)
        messages.append(
            build_message(
                mail_from=mail_from,
                to_addr=to_addr,
                subject=subject,
                body=body,
                is_html=is_html,
                encoding=enc,
            )
        )

    await send_batch_via_proxy(
        proxy,
        smtp_host=host,
        smtp_port=port,
        login=user or "",
        password=password or "",
        messages=messages,
        parallel=parallel,
    )
    return encodings
