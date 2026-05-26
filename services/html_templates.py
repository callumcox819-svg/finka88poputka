"""HTML-шаблоны по сервису Aqua (Tori.fi / data/HTMLfi)."""

from __future__ import annotations

from pathlib import Path

from region import HTML_DATA_DIR
from services.aqua_keys import GAG_SERVICE_KEY, aqua_service_for_html_dir
from services.gag_keys import (
    is_valid_gag_service,
    normalize_gag_service,
)
from services.user_settings import get_setting

HTML_ROOT = Path(__file__).resolve().parent.parent / "data" / HTML_DATA_DIR

GO_FILENAME = "confirmation.html"
BACK_FILENAME = "return.html"


def html_subdir_for_service(service_code: str | None) -> str | None:
    if not is_valid_gag_service(service_code):
        return None
    sub = aqua_service_for_html_dir(service_code)
    return sub or None


def html_template_path(service_code: str | None, filename: str) -> Path | None:
    sub = html_subdir_for_service(service_code)
    if not sub:
        return None
    p = HTML_ROOT / sub / filename
    return p if p.is_file() else None


def list_html_templates_for_service(service_code: str | None) -> list[str]:
    sub = html_subdir_for_service(service_code)
    if not sub:
        return []
    d = HTML_ROOT / sub
    if not d.is_dir():
        return []
    return sorted(f.name for f in d.glob("*.html"))


def service_label_for_path(subdir: str) -> str:
    if subdir == "tori_fi":
        return "Tori.fi"
    return subdir


def canonical_service_name(service_code: str | None) -> str | None:
    return normalize_gag_service(service_code)


async def load_html_template_for_user(
    user_id: int, filename: str
) -> tuple[str, str | None]:
    raw = (await get_setting(user_id, GAG_SERVICE_KEY) or "").strip()
    if not is_valid_gag_service(raw):
        return (
            "",
            "Сервис не настроен. Открой ⚙️ Настройки → 📋 Профиль → 🆔 profileID.",
        )
    sub = html_subdir_for_service(raw)
    p = html_template_path(raw, filename)
    if not p:
        label = service_label_for_path(sub or "")
        return "", f"Шаблон {filename} не найден для сервиса {label}."
    try:
        return p.read_text(encoding="utf-8", errors="ignore"), None
    except Exception as e:
        return "", f"Ошибка чтения шаблона: {e}"
