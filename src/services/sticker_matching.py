from __future__ import annotations

from src.utils.normalization import normalize_sticker_code


def match_by_sticker_code(excel_codes: list[str], catalog_codes: list[str]) -> dict[str, str | None]:
    catalog = {normalize_sticker_code(code): code for code in catalog_codes}
    return {code: catalog.get(normalize_sticker_code(code)) for code in excel_codes}

