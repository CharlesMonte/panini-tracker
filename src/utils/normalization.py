from __future__ import annotations

import re
import unicodedata


def normalize_person_name(name: str) -> str:
    return " ".join(str(name or "").strip().split())


def normalize_sticker_code(raw: str) -> str:
    value = str(raw or "").strip().upper()
    if not value:
        return ""
    value = value.replace(" ", "").replace("-", "").replace("_", "")
    value = re.sub(r"\.0$", "", value)
    match = re.fullmatch(r"([A-Z]+)0*(\d+)", value)
    if match:
        return f"{match.group(1)}{int(match.group(2))}"
    if re.fullmatch(r"\d+", value):
        return value.zfill(2) if int(value) == 0 else str(int(value))
    return value


def split_sticker_code(code: str) -> tuple[str | None, int | None]:
    normalized = normalize_sticker_code(code)
    match = re.fullmatch(r"([A-Z]+)(\d+)", normalized)
    if match:
        return match.group(1), int(match.group(2))
    if re.fullmatch(r"\d+", normalized):
        return None, int(normalized)
    return None, None


def make_display_code(code: str) -> str:
    normalized = normalize_sticker_code(code)
    category_code, number = split_sticker_code(normalized)
    if category_code and number is not None:
        return f"{category_code}-{number}"
    return normalized


def normalize_search_text(value: str | None) -> str:
    text = unicodedata.normalize("NFKD", str(value or ""))
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return re.sub(r"\s+", " ", text).strip().lower()

