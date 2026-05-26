"""
Отдельный процесс только для входящей почты (IMAP).

Railway: второй сервис из того же репозитория norwa88:
  python imap_worker.py

Общее с ботом: DATABASE_URL, BOT_TOKEN (только send_message, без polling).
На сервисе norwa88 (бот): IMAP_DEDICATED_WORKER=1 — IMAP не дублируется в bot.py.
"""

from __future__ import annotations

import asyncio
import logging
import os
import sys

from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from config import load_settings
from database import count_imap_poll_accounts_raw, init_db, list_imap_poll_accounts
from services.bot_users import seed_config_admins
from services.db_backend import DB_PATH, database_env_diag, is_postgres, pg_connection_label
from services.incoming_worker import POLL_SEC, start_incoming_mail_worker

logger = logging.getLogger(__name__)


def _truthy(name: str) -> bool:
    return (os.getenv(name) or "").strip().lower() in {"1", "true", "yes", "on"}


async def _log_smtp_stats() -> dict:
    stats = await count_imap_poll_accounts_raw()
    logger.info(
        "IMAP DB (%s): smtp total=%s enabled=%s with_password=%s pollable=%s",
        pg_connection_label(),
        stats["total"],
        stats["enabled"],
        stats["with_password"],
        stats["pollable"],
    )
    return stats


async def _wait_until_pollable() -> dict:
    """Не падать на пустой БД — ждать, пока ящики добавят в боте."""
    interval = max(15, int(os.getenv("IMAP_EMPTY_DB_RETRY_SEC", "30")))
    max_wait = int(os.getenv("IMAP_EMPTY_DB_MAX_WAIT_SEC", "0"))  # 0 = ждать бесконечно
    elapsed = 0
    while True:
        stats = await _log_smtp_stats()
        if stats["pollable"] > 0:
            return stats
        if stats["enabled"] > 0:
            logger.warning(
                "0 ящиков для IMAP при %s enabled SMTP — нет пароля или IMAP host. "
                "Проверьте ⚡ Быстрое добавление в боте. Повтор через %ss.",
                stats["enabled"],
                interval,
            )
        else:
            logger.warning(
                "Postgres подключён (%s), но SMTP-ящиков пока 0 — это не ошибка DATABASE_URL. "
                "Добавьте почту в norwa88: ⚡ Быстрое добавление. Повтор через %ss.",
                pg_connection_label(),
                interval,
            )
        if max_wait > 0 and elapsed >= max_wait:
            logger.critical(
                "За %ss так и не появилось pollable>0. Если в логах norwa88 pollable>0, "
                "а здесь 0 — разные БД: на обоих сервисах Reference → один Postgres.DATABASE_URL.",
                max_wait,
            )
            sys.exit(1)
        await asyncio.sleep(interval)
        elapsed += interval


async def _worker_heartbeat() -> None:
    n = 0
    while True:
        await asyncio.sleep(60)
        n += 1
        try:
            accs = await list_imap_poll_accounts()
            n_acc = len(accs)
            n_users = len({int(a.get("user_id") or 0) for a in accs})
        except Exception:
            n_acc, n_users = "?", "?"
        logger.info(
            "💓 IMAP worker alive #%s mailboxes=%s users=%s poll=%ss max_concurrent=%s",
            n,
            n_acc,
            n_users,
            POLL_SEC,
            os.getenv("MAX_IMAP_CONCURRENT", "8"),
        )


async def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        stream=sys.stdout,
    )

    logger.info("Старт imap_worker | %s", database_env_diag())

    # Отдельный процесс = входящая почта всегда включена (не требуем ENABLE_INCOMING_MAIL в Railway).
    if not _truthy("ENABLE_INCOMING_MAIL"):
        logger.warning(
            "ENABLE_INCOMING_MAIL не задан в Railway — для imap_worker.py это нормально, "
            "опрос IMAP всё равно запускается."
        )

    wait_sec = int(os.getenv("DATABASE_URL_WAIT_SEC", "90"))
    for attempt in range(max(1, wait_sec // 15)):
        if is_postgres():
            break
        logger.warning(
            "PostgreSQL не найден (попытка %s). %s",
            attempt + 1,
            database_env_diag(),
        )
        await asyncio.sleep(15)
    else:
        logger.critical(
            "PostgreSQL так и не появился (%s). %s\n"
            "Частая причина на Railway: переменная DATABASE_URL есть в UI, но "
            "<пустая строка> или <нет в процессе>. Удалите DATABASE_URL вручную → "
            "на схеме проекта соедините Postgres с imap-worker → "
            "Variables → Add Reference → Postgres.DATABASE_URL → Redeploy.\n"
            "План Б (сразу письма в TG): на norwa88 уберите IMAP_DEDICATED_WORKER, "
            "добавьте ENABLE_INCOMING_MAIL=1, остановите imap-worker.",
            DB_PATH,
            database_env_diag(),
        )
        sys.exit(1)

    settings = load_settings()
    await init_db()
    await seed_config_admins(settings.admin_ids)

    if os.getenv("IMAP_EXIT_IF_NO_MAILBOXES", "").strip().lower() in {"1", "true", "yes"}:
        stats = await _log_smtp_stats()
        if stats["pollable"] == 0:
            logger.critical(
                "IMAP_EXIT_IF_NO_MAILBOXES=1 и pollable=0 — выход. "
                "Уберите переменную или добавьте ящики в боте."
            )
            sys.exit(1)
    else:
        stats = await _wait_until_pollable()
    logger.info("Готово к опросу: pollable=%s", stats["pollable"])

    os.environ.setdefault("MAX_IMAP_CONCURRENT", "12")

    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )

    me = await bot.get_me()
    logger.info(
        "IMAP worker: @%s (id=%s) — polling Telegram НЕ запускается",
        me.username,
        me.id,
    )

    delay = int(os.getenv("INCOMING_MAIL_START_DELAY_SEC", "10"))
    if delay > 0:
        logger.info("Старт опроса ящиков через %ss", delay)
        await asyncio.sleep(delay)

    start_incoming_mail_worker(bot)
    asyncio.create_task(_worker_heartbeat())

    try:
        await asyncio.Event().wait()
    finally:
        await bot.session.close()
        logger.info("IMAP worker stopped")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
