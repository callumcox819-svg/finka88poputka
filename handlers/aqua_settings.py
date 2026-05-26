"""Aqua / GOO Network: profileID и личный User API key."""

from __future__ import annotations

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from keyboards.main_menu import main_keyboard
from region import AQUA_DEFAULT_SERVICE, AQUA_GENERATE_DOMAIN
from services.aqua_keys import AQUA_PROFILE_ID_KEY, AQUA_USER_API_KEY, global_team_aqua_api_key
from services.aqua_user import format_aqua_profile_message, load_aqua_profile
from services.user_settings import get_setting, set_setting
from utils.callback_edit import cq_edit_text
from utils.secrets import clean_secret
from utils.text_html import e

router = Router(name="aqua_settings")


class AquaKeysState(StatesGroup):
    user_key = State()


class AquaProfileState(StatesGroup):
    profile_id = State()


def _back_settings() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="settings_open")]
        ]
    )


def _profile_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🆔 profileID (Aqua)", callback_data="aqua_set:profile_id"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🔑 User API key", callback_data="aqua_set:user_key"
                )
            ],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="settings_open")],
            [InlineKeyboardButton(text="🍀 Скрыть", callback_data="ref_hide")],
        ]
    )


async def _render_profile(target: Message | CallbackQuery, *, edit: bool = False) -> None:
    uid = int(target.from_user.id)
    un = (target.from_user.username or "").strip()
    p = await load_aqua_profile(uid, username=un, telegram_id=uid)
    team_ok = bool(global_team_aqua_api_key() or p.team_key_set)
    team_line = (
        "🟢 Team key на сервере"
        if team_ok
        else "🔴 Team key: <code>AQUA_TEAM_API_KEY</code> в Railway"
    )
    text = (
        format_aqua_profile_message(p)
        + f"\n\n{team_line}\n"
        f"🌐 <code>{e(AQUA_GENERATE_DOMAIN)}</code> · 📦 <code>{e(AQUA_DEFAULT_SERVICE)}</code>"
    )
    kb = _profile_kb()
    if isinstance(target, CallbackQuery):
        await cq_edit_text(target, text, reply_markup=kb)
    elif edit and target.bot:
        await target.bot.edit_message_text(
            text,
            chat_id=target.chat.id,
            message_id=target.message_id,
            reply_markup=kb,
            parse_mode="HTML",
        )
    else:
        await target.answer(text, reply_markup=kb, parse_mode="HTML")


@router.message(F.text.in_({"📋 Профиль", "Профиль"}))
async def cmd_profile_legacy(message: Message, state: FSMContext) -> None:
    await state.clear()
    await _render_profile(message)


@router.callback_query(F.data.in_({"aqua_show:profile", "gag_show:profile"}))
async def aqua_show_profile(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await _render_profile(callback)
    await callback.answer()


@router.callback_query(
    F.data.in_(
        {
            "aqua_show:keys",
            "gag_show:key",
            "aqua_show:key",
            "aqua_api_docs",
            "aqua_profile_edit",
        }
    )
)
async def aqua_legacy_callbacks(callback: CallbackQuery, state: FSMContext) -> None:
    """Старые кнопки → экран профиля."""
    await aqua_show_profile(callback, state)


@router.callback_query(F.data == "aqua_set:user_key")
async def aqua_set_user_key(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(AquaKeysState.user_key)
    cur = (await get_setting(callback.from_user.id, AQUA_USER_API_KEY) or "").strip()
    hint = f"{cur[:8]}…" if len(cur) > 8 else (cur or "—")
    await cq_edit_text(
        callback,
        "✍️ <b>User API key</b> (личный, для генерации)\n\n"
        f"Сейчас: <code>{e(hint)}</code>\n\n"
        "Отмена: <code>-</code>",
        reply_markup=_back_settings(),
    )
    await callback.answer()


@router.message(AquaKeysState.user_key)
async def aqua_save_user_key(message: Message, state: FSMContext) -> None:
    raw = (message.text or "").strip()
    if raw == "-":
        await state.clear()
        await message.answer("Отменено.", reply_markup=main_keyboard())
        return
    val = clean_secret(raw)
    if not val:
        await message.answer("Пустой ключ.")
        return
    await set_setting(message.from_user.id, AQUA_USER_API_KEY, val)
    await state.clear()
    await message.answer("✅ User API key сохранён.", reply_markup=main_keyboard())


@router.callback_query(F.data == "aqua_set:profile_id")
async def aqua_set_profile_id_start(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(AquaProfileState.profile_id)
    cur = (await get_setting(callback.from_user.id, AQUA_PROFILE_ID_KEY) or "").strip()
    await cq_edit_text(
        callback,
        "🆔 <b>profileID</b> из Aqua\n\n"
        f"Сейчас: <code>{e(cur or '—')}</code>\n\n"
        "Зелёный токен из профиля Aqua.\n"
        "Отмена: <code>-</code>",
        reply_markup=_back_settings(),
    )
    await callback.answer()


@router.message(AquaProfileState.profile_id)
async def aqua_save_profile_id(message: Message, state: FSMContext) -> None:
    raw = (message.text or "").strip()
    if raw == "-":
        await state.clear()
        await message.answer("Отменено.", reply_markup=main_keyboard())
        return
    pid = clean_secret(raw)
    if not pid:
        await message.answer("Пустой profileID.")
        return
    await set_setting(message.from_user.id, AQUA_PROFILE_ID_KEY, pid)
    await set_setting(message.from_user.id, "aqua_service", AQUA_DEFAULT_SERVICE)
    await state.clear()
    await message.answer("✅ profileID сохранён.", reply_markup=main_keyboard())
