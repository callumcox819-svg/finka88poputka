"""Карточка GAG-ссылки — reply к письму (оформление как happy88)."""

from __future__ import annotations

import logging

from aiogram import Bot
from aiogram.types import BufferedInputFile, InlineKeyboardButton, InlineKeyboardMarkup

from services.link_id import format_incoming_link_id

logger = logging.getLogger(__name__)


def _service_label_for_card(service_label: str) -> str:
    s = (service_label or "").strip()
    return s or "Marketplace"


def build_link_card_caption(
    *,
    offer_title: str,
    offer_price: str,
    profile_title: str,
    service_label: str,
    item_link: str,
    gag_link: str,
    link_id_display: str | None = None,
) -> str:
    svc = _service_label_for_card(service_label)
    link_ad = (item_link or "").strip()
    if link_ad:
        svc_line = f'📢 <b>Объявления » <a href="{e(link_ad)}">{e(svc)}</a></b>'
    else:
        svc_line = f"📢 <b>Объявления » {e(svc)}</b>"

    prof = (profile_title or "").strip() or "—"
    title = (offer_title or "").strip() or "—"
    price = (offer_price or "").strip() or "—"
    url = (gag_link or "").strip()
    id_line = ""
    lid = (link_id_display or "").strip()
    if lid:
        id_line = f"🆔 <b>ID:</b> <code>{e(lid)}</code>\n\n"

    return (
        f"{svc_line}\n\n"
        f"📌 <b>Название:</b> {e(title)}\n"
        f"💰 <b>Цена:</b> {e(price)}\n"
        f"👤 <b>Профиль:</b> <b>{e(prof)}</b>\n\n"
        f"{id_line}"
        f"🔗 <b>Ссылка:</b>\n<a href=\"{e(url)}\">{e(url)}</a>"
    )


def build_link_card_keyboard(
    *,
    lead_id: int | None,
    mail_id: int | None = None,
) -> InlineKeyboardMarkup | None:
    if not lead_id or int(lead_id) <= 0:
        return None
    rows: list[list[InlineKeyboardButton]] = [
        [
            InlineKeyboardButton(
                text="💶 Цена",
                callback_data=f"lead_price:{int(lead_id)}",
            )
        ],
    ]
    if mail_id:
        rows.append(
            [
                InlineKeyboardButton(
                    text="🔄 Пересоздать ссылку",
                    callback_data=f"goo_regen:{int(mail_id)}",
                )
            ]
        )
    return InlineKeyboardMarkup(inline_keyboard=rows)


async def _photo_for_telegram(photo_url: str) -> str | BufferedInputFile:
    """Скачать фото — меньше размытых полос у узких превью с CDN."""
    url = (photo_url or "").strip()
    if not url:
        return url
    try:
        import aiohttp

        timeout = aiohttp.ClientTimeout(total=20)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(url) as resp:
                if resp.status != 200:
                    return url
                data = await resp.read()
                if len(data) < 400:
                    return url
                ctype = (resp.headers.get("Content-Type") or "").lower()
                ext = "jpg"
                if "png" in ctype:
                    ext = "png"
                elif "webp" in ctype:
                    ext = "webp"
                return BufferedInputFile(data, filename=f"offer.{ext}")
    except Exception as exc:
        logger.debug("link card photo download failed: %s", exc)
        return url


async def send_generated_link_card(
    bot: Bot,
    chat_id: int,
    *,
    offer_title: str,
    offer_price: str,
    photo_url: str,
    profile_title: str,
    service_label: str,
    item_link: str,
    link: str,
    anchor_message_id: int,
    lead_id: int | None = None,
    mail_id: int | None = None,
    gag_ad_id: str | None = None,
) -> int | None:
    """
    Фото + поля + кнопка «💶 Цена». Reply к карточке письма.
    Возвращает message_id отправленной карточки ссылки.
    """
    card_text = build_link_card_caption(
        offer_title=offer_title,
        offer_price=offer_price,
        profile_title=profile_title,
        service_label=service_label,
        item_link=item_link,
        gag_link=link,
        link_id_display=format_incoming_link_id(
            link,
            gag_ad_id=gag_ad_id,
            item_link=item_link,
        ),
    )
    price_kb = build_link_card_keyboard(lead_id=lead_id, mail_id=mail_id)
    reply_to = int(anchor_message_id)
    p = (photo_url or "").strip()
    sent_id: int | None = None

    if not p:
        m = await bot.send_message(
            chat_id,
            card_text + "\n\n<i>Фото объявления не найдено в БД.</i>",
            parse_mode="HTML",
            reply_markup=price_kb,
            reply_to_message_id=reply_to,
        )
        sent_id = m.message_id
    else:
        photo = await _photo_for_telegram(p)
        try:
            m = await bot.send_photo(
                chat_id=chat_id,
                photo=photo,
                caption=card_text,
                parse_mode="HTML",
                reply_markup=price_kb,
                reply_to_message_id=reply_to,
            )
            sent_id = m.message_id
        except Exception:
            logger.warning("send_photo link card failed, fallback to text")
            m = await bot.send_message(
                chat_id,
                card_text + "\n\n<i>Не удалось отправить фото.</i>",
                parse_mode="HTML",
                reply_markup=price_kb,
                reply_to_message_id=reply_to,
            )
            sent_id = m.message_id

    try:
        await bot.pin_chat_message(chat_id, reply_to, disable_notification=True)
    except Exception:
        pass

    return sent_id
