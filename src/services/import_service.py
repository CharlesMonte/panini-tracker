from __future__ import annotations

from pathlib import Path

from sqlalchemy.orm import Session

from src.services.excel_import import import_excel, preview_excel
from src.services.source_names_import import enrich_stickers_from_source_names


def preview_excel_import(path: str | Path):
    return preview_excel(path)


def run_excel_import(session: Session, path: str | Path) -> dict:
    return import_excel(session, path, source_path=str(path))


def run_source_names_import(session: Session, path: str | Path = "source_names.txt") -> dict:
    return enrich_stickers_from_source_names(session, path)
