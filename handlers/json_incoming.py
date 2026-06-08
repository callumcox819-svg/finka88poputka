"""Автоматическая обработка JSON void-parser (файл или текст в чат)."""

from __future__ import annotations

import asyncio
import json
import logging

from aiogram import F, Router
from aiogram.filters import BaseFilter
from aiogram.types import Message

from config import Settings
from services.void_parser import parse_void_json_bytes, parse_void_json_text
from services.void_validation_runner import run_void_validation

router = Router()
logger = logging.getLogger(__name__)

_DOWNLOAD_TIMEOUT_SEC = 45.0


class JsonDocumentFilter(BaseFilter):
    async def __call__(self, message: Message) -> bool:
        doc = message.document
        return bool(doc and doc.file_name and doc.file_name.lower().endswith(".json"))


class JsonTextFilter(BaseFilter):
    async def __call__(self, message: Message) -> bool:
        text = (message.text or "").strip()
        return bool(text) and text[0] in "{["


async def _edit_status(message: Message, status, text: str) -> None:
    try:
        await status.edit_text(text, parse_mode="HTML")
    except Exception:
        try:
            await message.answer(text, parse_mode="HTML")
        except Exception:
            pass


@router.message(F.document, JsonDocumentFilter())
async def on_json_document(message: Message, bot, settings: Settings) -> None:
    doc = message.document
    assert doc

    status = await message.answer("⏳ Загружаю JSON…")

    try:
        file = await asyncio.wait_for(bot.get_file(doc.file_id), timeout=_DOWNLOAD_TIMEOUT_SEC)
        buf = await asyncio.wait_for(
            bot.download_file(file.file_path),
            timeout=_DOWNLOAD_TIMEOUT_SEC,
        )
        raw = buf.read() if hasattr(buf, "read") else bytes(buf or b"")
        items = parse_void_json_bytes(raw)
    except asyncio.TimeoutError:
        await _edit_status(
            message,
            status,
            "❌ Telegram не отдал файл (таймаут). Повторите через минуту.\n"
            "<i>Если в логах TelegramConflictError — остановите второй экземпляр бота.</i>",
        )
        return
    except json.JSONDecodeError:
        await _edit_status(message, status, "❌ Не удалось разобрать JSON.")
        return
    except Exception as exc:
        logger.exception("json download failed")
        await _edit_status(message, status, f"❌ Ошибка загрузки: {exc}")
        return

    if not items:
        await _edit_status(
            message,
            status,
            "В файле нет массива <code>items</code>.",
        )
        return

    await _edit_status(
        message,
        status,
        f"🔎 Подбор email… <b>0/{len(items)}</b>\n<i>ValidEmail, подождите…</i>",
    )

    u = message.from_user
    try:
        await run_void_validation(
            bot,
            settings,
            u.id,
            message.chat.id,
            items,
            status_message_id=status.message_id,
            username=(u.username or "") if u else "",
        )
    except Exception as exc:
        logger.exception("run_void_validation failed user_id=%s", u.id)
        await _edit_status(
            message,
            status,
            f"❌ Ошибка запуска подбора: <code>{type(exc).__name__}</code>\n{str(exc)[:300]}",
        )


@router.message(F.text, JsonTextFilter())
async def on_json_text(message: Message, bot, settings: Settings) -> None:
    text = (message.text or "").strip()
    try:
        items = parse_void_json_text(text)
    except json.JSONDecodeError:
        await message.answer("❌ Неверный JSON.")
        return

    if not items:
        await message.answer("В JSON нет объявлений (items).")
        return

    status = await message.answer(
        f"🔎 Подбор email… <b>0/{len(items)}</b>\n<i>ValidEmail, подождите…</i>",
        parse_mode="HTML",
    )

    u = message.from_user
    try:
        await run_void_validation(
            bot,
            settings,
            u.id,
            message.chat.id,
            items,
            status_message_id=status.message_id,
            username=(u.username or "") if u else "",
        )
    except Exception as exc:
        logger.exception("run_void_validation failed user_id=%s", u.id)
        await _edit_status(
            message,
            status,
            f"❌ Ошибка запуска подбора: <code>{type(exc).__name__}</code>\n{str(exc)[:300]}",
        )
