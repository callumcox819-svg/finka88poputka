"""ID из сгенерированной Aqua/GOO-ссылки и объявления."""

from __future__ import annotations

import re
from urllib.parse import parse_qs, urlparse

_DIGIT_SEGMENT_RE = re.compile(r"(?:^|/)(\d{5,})(?:/|$|\?|#)")
_SLUG_SEGMENT_RE = re.compile(r"^[A-Za-z0-9_-]{6,64}$")
_ITEM_AD_RE = re.compile(r"/item/(\d+)", re.I)


def slug_from_generated_url(url: str | None) -> str | None:
    """Slug из path, напр. …/receive/order/uOFSfJFCbT → uOFSfJFCbT."""
    u = (url or "").strip()
    if not u:
        return None
    try:
        parsed = urlparse(u)
    except Exception:
        return None
    parts = [p for p in (parsed.path or "").split("/") if p]
    for seg in reversed(parts):
        if seg.isdigit():
            continue
        if _SLUG_SEGMENT_RE.match(seg):
            return seg
    return None


def link_id_from_generated_url(url: str | None) -> str | None:
    """Числовой id или slug из сгенерированной ссылки."""
    u = (url or "").strip()
    if not u:
        return None

    slug = slug_from_generated_url(u)
    if slug:
        return slug

    try:
        parsed = urlparse(u)
    except Exception:
        return None

    parts = [p for p in (parsed.path or "").split("/") if p]
    for seg in reversed(parts):
        if seg.isdigit() and len(seg) >= 5:
            return seg

    try:
        qs = parse_qs(parsed.query or "")
        for key in ("id", "adId", "ad_id", "order_id", "orderId"):
            vals = qs.get(key) or []
            if vals and str(vals[0]).strip().isdigit():
                return str(vals[0]).strip()
    except Exception:
        pass

    m = _DIGIT_SEGMENT_RE.search(u)
    if m:
        return m.group(1)
    return None


def listing_ad_ref_from_item_link(item_link: str | None) -> str | None:
    """#ad… из ссылки объявления (Facebook Marketplace и др.)."""
    u = (item_link or "").strip()
    if not u:
        return None
    m = _ITEM_AD_RE.search(u)
    if m:
        return f"#ad{m.group(1)}"
    m = re.search(r"/(\d{8,})(?:/|$|\?)", u)
    if m:
        return f"#ad{m.group(1)}"
    return None


def format_incoming_link_id(
    generated_url: str | None,
    *,
    gag_ad_id: str | None = None,
    item_link: str | None = None,
) -> str | None:
    """
    Строка для карточки: uOFSfJFCbT (#ad824240258).
    Slug — из Aqua-ссылки; (#ad…) — из объявления или gag_ad_id в БД.
    """
    slug = slug_from_generated_url(generated_url) or (
        (gag_ad_id or "").strip()
        if (gag_ad_id or "").strip() and not str(gag_ad_id).strip().isdigit()
        else None
    )
    if not slug:
        slug = link_id_from_generated_url(generated_url)

    ad_ref = listing_ad_ref_from_item_link(item_link)
    if not ad_ref:
        raw = (gag_ad_id or "").strip()
        if raw:
            if raw.startswith("#ad"):
                ad_ref = raw
            elif raw.isdigit():
                ad_ref = f"#ad{raw}"
            elif raw.startswith("ad") and raw[2:].isdigit():
                ad_ref = f"#{raw}"

    if slug and ad_ref:
        return f"{slug} ({ad_ref})"
    if slug:
        return slug
    if ad_ref:
        return ad_ref
    return None
