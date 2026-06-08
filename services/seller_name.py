"""Имя продавца из JSON → local-part для email (имя@домен)."""

from __future__ import annotations

import re
import unicodedata
from typing import Any

MIN_NAME_ALNUM = 3

# Союзы «и» — убираем во втором варианте (Leena ja Pauli → leena.pauli).
NAME_CONNECTORS = frozenset(
    {
        "ja",
        "och",
        "and",
        "og",
        "und",
        "plus",
    }
)

_LATIN_FOLD = str.maketrans(
    {
        "ö": "o",
        "Ö": "O",
        "ä": "a",
        "Ä": "A",
        "ü": "u",
        "Ü": "U",
        "ë": "e",
        "Ë": "E",
        "é": "e",
        "è": "e",
        "ê": "e",
        "á": "a",
        "à": "a",
        "â": "a",
        "í": "i",
        "ì": "i",
        "î": "i",
        "ó": "o",
        "ò": "o",
        "ô": "o",
        "ú": "u",
        "ù": "u",
        "û": "u",
        "ñ": "n",
        "ç": "c",
        "ø": "o",
        "Ø": "O",
        "å": "a",
        "Å": "A",
        "æ": "ae",
        "Æ": "AE",
        "œ": "oe",
        "Œ": "OE",
        "ß": "ss",
        "ẞ": "SS",
    }
)


def seller_name_from_item(item: dict[str, Any]) -> str:
    if not isinstance(item, dict):
        return ""
    return str(
        item.get("item_person_name")
        or item.get("person_name")
        or item.get("name")
        or ""
    ).strip()


def normalize_seller_name(raw: str) -> str:
    if not raw:
        return ""
    s = " ".join(str(raw).strip().split())
    s = s.translate(_LATIN_FOLD)
    normalized = unicodedata.normalize("NFD", s)
    s = "".join(ch for ch in normalized if unicodedata.category(ch) != "Mn")
    return s


def count_name_alnum(name: str) -> int:
    return sum(1 for c in normalize_seller_name(name) if c.isalnum())


def seller_name_eligible(name: str, *, min_alnum: int = MIN_NAME_ALNUM) -> bool:
    return count_name_alnum(name) >= min_alnum


def split_name_parts(name: str) -> list[str]:
    """
    Части имени для local-part: пробел, дефис, апостроф.
    hanne-elina → hanne, elina; seppo Olli → seppo, olli.
    """
    norm = normalize_seller_name(name)
    if not norm:
        return []
    parts = re.split(r"[\s\-']+", norm.strip())
    tokens: list[str] = []
    seen: set[str] = set()
    for part in parts:
        clean = re.sub(r"[^A-Za-z0-9]", "", part)
        if not clean:
            continue
        token = clean.lower()
        if token in seen:
            continue
        seen.add(token)
        tokens.append(token)
    return tokens


def _clean_local(local: str) -> str:
    s = re.sub(r"[^a-z0-9.]", "", (local or "").lower())
    return re.sub(r"\.+", ".", s).strip(".")


def make_email_local_variants(name: str) -> list[str]:
    """
    Варианты local-part по приоритету:
    - все части: hanne.elina, seppo.olli, leena.ja.pauli
    - без союзов: leena.pauli
    - первое.последнее (если отличается)
    - одно слово: karina
    """
    tokens = split_name_parts(name)
    if not tokens:
        return []

    out: list[str] = []
    seen: set[str] = set()

    def add(local: str) -> None:
        cleaned = _clean_local(local)
        if cleaned and cleaned not in seen:
            seen.add(cleaned)
            out.append(cleaned)

    add(".".join(tokens))

    substantive = [t for t in tokens if t not in NAME_CONNECTORS]
    if len(substantive) >= 2:
        add(".".join(substantive))
        add(f"{substantive[0]}.{substantive[-1]}")
        if len(substantive) == 2:
            add(f"{substantive[0]}{substantive[-1]}")
    elif len(substantive) == 1:
        add(substantive[0])

    return out


def make_email_local(name: str) -> str:
    """Основной local-part (первый вариант из make_email_local_variants)."""
    variants = make_email_local_variants(name)
    return variants[0] if variants else ""


def display_local(name: str) -> str:
    """Для сообщений: Hanne.Elina, Leena.Ja.Pauli."""
    local = make_email_local(name)
    if not local:
        return ""
    if "." not in local:
        return local[:1].upper() + local[1:] if local else ""
    return ".".join(p.capitalize() for p in local.split("."))
