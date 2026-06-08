"""Пул SOCKS5: все живые прокси по очереди, без привязок к аккаунтам."""

from __future__ import annotations

from database import list_sendable_proxies, note_proxy_last_error

_rr_index: dict[int, int] = {}

def reset_round_robin(user_id: int) -> None:
    _rr_index.pop(int(user_id), None)


def proxy_to_dict(row: dict) -> dict:
    return {
        "id": row["id"],
        "host": row["host"],
        "port": int(row["port"]),
        "username": row.get("username"),
        "password": row.get("password"),
        "type": row.get("proxy_type") or "socks5",
    }


async def pick_first_proxy(user_id: int) -> dict | None:
    """Первый живой прокси — для быстрой рассылки (без ротации)."""
    rows = await list_sendable_proxies(user_id)
    if not rows:
        return None
    return proxy_to_dict(rows[0])


async def pick_next_proxy(user_id: int) -> dict | None:
    rows = await list_sendable_proxies(user_id)
    if not rows:
        return None
    uid = int(user_id)
    idx = _rr_index.get(uid, 0) % len(rows)
    _rr_index[uid] = idx + 1
    return proxy_to_dict(rows[idx])


def is_proxy_tunnel_error(exc: BaseException) -> bool:
    """Только явные ошибки SOCKS/прокси (не любой SMTP «connection»)."""
    err_l = str(exc).lower()
    if "generalproxyerror" in err_l:
        return True
    if "socks" in err_l and any(
        m in err_l for m in ("error", "failed", "failure", "unable", "cannot", "refused")
    ):
        return True
    if "proxy" in err_l and any(
        m in err_l for m in ("error", "failed", "failure", "unable", "cannot", "refused", "tunnel")
    ):
        return True
    return False


async def note_proxy_send_error(
    user_id: int, proxy_id: int, error: str
) -> None:
    """Записать ошибку отправки, не исключая прокси из пула."""
    await note_proxy_last_error(
        proxy_id,
        user_id,
        (error or "SMTP via proxy failed")[:500],
    )


async def mark_proxy_mailing_dead(
    user_id: int, proxy_id: int, error: str
) -> None:
    await note_proxy_send_error(user_id, proxy_id, error)
