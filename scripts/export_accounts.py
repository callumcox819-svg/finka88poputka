"""Выгрузка email:password активных ящиков пользователя (Railway: railway run python scripts/export_accounts.py USER_ID)."""

from __future__ import annotations

import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


async def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python scripts/export_accounts.py USER_ID [--all]")
        sys.exit(1)

    user_id = int(sys.argv[1])
    active_only = "--all" not in sys.argv[2:]

    from database import init_db, list_all_smtp_accounts

    await init_db()
    accounts = await list_all_smtp_accounts(user_id, with_secrets=True)
    if active_only:
        accounts = [
            a
            for a in accounts
            if int(a.get("enabled", 1)) and int(a.get("smtp_enabled", 1))
        ]

    lines: list[str] = []
    for a in accounts:
        email = (a.get("email") or "").strip()
        password = (a.get("password") or "").strip()
        if email and password:
            lines.append(f"{email}:{password}")

    print(f"# user_id={user_id} active_only={active_only} count={len(lines)}")
    for line in lines:
        print(line)


if __name__ == "__main__":
    asyncio.run(main())
