"""Пул ValidEmail: несколько API-ключей, домены по приоритету (как happy88)."""

from __future__ import annotations

import asyncio
import logging
import os
from typing import Any

from services.validemail_api import validate_email_api

logger = logging.getLogger(__name__)

RATE_LIMIT_BACKOFF_SEC = float(os.getenv("VALIDEMAIL_RATE_LIMIT_BACKOFF_SEC", "10"))
RATE_LIMIT_RETRIES = max(1, int(os.getenv("VALIDEMAIL_RATE_LIMIT_RETRIES", "4")))


class ValidemailKeyPool:
    """
    Несколько ключей — у каждого свой лимит параллельных запросов.
    Мёртвый ключ (payment_required) пропускается, запрос идёт на следующий.
    """

    def __init__(
        self,
        api_keys: list[str],
        *,
        url: str,
        timeout_sec: int,
        concurrency_per_key: int,
    ) -> None:
        keys = [k.strip() for k in api_keys if (k or "").strip()]
        if not keys:
            raise ValueError("no validemail api keys")
        self._keys = keys
        self._url = url
        self._timeout = timeout_sec
        self._sems = [
            asyncio.Semaphore(max(1, concurrency_per_key)) for _ in keys
        ]
        self._rr = 0
        self._pick_lock = asyncio.Lock()
        self._dead: set[int] = set()

    @property
    def key_count(self) -> int:
        return len(self._keys)

    @property
    def live_key_count(self) -> int:
        return max(0, len(self._keys) - len(self._dead))

    def mark_dead(self, key_index: int, reason: str = "") -> None:
        idx = int(key_index)
        if idx in self._dead or idx < 0 or idx >= len(self._keys):
            return
        self._dead.add(idx)
        logger.warning(
            "ValidEmail key %s/%s disabled (%s), live=%s",
            idx + 1,
            len(self._keys),
            reason or "dead",
            self.live_key_count,
        )

    async def _pick_live_index(self) -> int | None:
        async with self._pick_lock:
            n = len(self._keys)
            if not n or len(self._dead) >= n:
                return None
            for _ in range(n):
                idx = self._rr % n
                self._rr += 1
                if idx not in self._dead:
                    return idx
            return None

    async def validate(self, email: str) -> tuple[bool, str, dict[str, Any]]:
        n = len(self._keys)
        tried = 0
        while tried < n:
            idx = await self._pick_live_index()
            if idx is None:
                return False, "payment_required", {}
            tried += 1
            async with self._sems[idx]:
                ok, reason, data = await validate_email_api(
                    email,
                    api_key=self._keys[idx],
                    url=self._url,
                    timeout_sec=self._timeout,
                )
            if reason == "payment_required":
                self.mark_dead(idx, "payment_required")
                continue
            return ok, reason, data
        return False, "payment_required", {}


async def find_deliverable_email(
    pool: ValidemailKeyPool,
    local: str,
    domains: list[str],
) -> tuple[str | None, str | None, str | None]:
    """
    Домены по приоритету; на продавца — первая валидная почта.

    Возвращает (email, domain, fatal_reason).
    fatal_reason = payment_required только если все ключи исчерпаны.
    """
    if not local or not domains:
        return None, None, None

    if pool.live_key_count <= 0:
        return None, None, "payment_required"

    for dom in domains:
        dom = (dom or "").strip().lower()
        if not dom:
            continue
        email = f"{local}@{dom}".lower()

        for attempt in range(RATE_LIMIT_RETRIES):
            if pool.live_key_count <= 0:
                return None, None, "payment_required"

            ok, reason, _ = await pool.validate(email)
            if ok:
                return email, dom, None
            if reason == "payment_required":
                if pool.live_key_count <= 0:
                    return None, None, "payment_required"
                continue
            if reason == "rate_limit":
                wait = RATE_LIMIT_BACKOFF_SEC * (attempt + 1)
                logger.warning(
                    "ValidEmail rate_limit %s, retry %s/%s in %ss",
                    email,
                    attempt + 1,
                    RATE_LIMIT_RETRIES,
                    wait,
                )
                await asyncio.sleep(wait)
                continue
            break

    return None, None, None
