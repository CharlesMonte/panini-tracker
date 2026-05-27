from __future__ import annotations

import re
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.models import Holding, ImportRun, Person, Sticker
from src.repositories import get_sticker_by_code, get_stickers
from src.utils.normalization import make_display_code, normalize_sticker_code, split_sticker_code


SOURCE_NAMES_IMPORT_TYPE = "source_names_txt"
SOURCE_CODE_ALIASES = {
    "KAS12": "KSA12",
    "SWI9": "SUI9",
    "SWI20": "SUI20",
}
EQUIVALENT_CODES = {
    "00": ["FWC0"],
    "FWC0": ["00"],
}
SPECIAL_PLAYERLESS_MARKERS = [
    "team photo",
    "team logo",
    "official ",
    "fifa museum",
    "host countries & cities",
    "panini logo",
]


def _strip_foil(label: str) -> str:
    return re.sub(r"\s+FOIL\b", "", label, flags=re.I).strip()


def parse_source_name_line(raw_line: str) -> dict | None:
    text = " ".join(str(raw_line or "").strip().split())
    if not text:
        return None
    match = re.match(r"^(\S+)\s+(.+)$", text)
    if not match:
        return None
    sticker_code = normalize_sticker_code(match.group(1))
    sticker_code = SOURCE_CODE_ALIASES.get(sticker_code, sticker_code)
    label = match.group(2).strip()
    label_without_foil = _strip_foil(label)
    is_foil = bool(re.search(r"\bFOIL\b", label, flags=re.I))
    is_team_photo = "team photo" in label_without_foil.lower()
    is_emblem = "team logo" in label_without_foil.lower() or "official emblem" in label_without_foil.lower()

    team_name = None
    player_name = None
    if " - " in label_without_foil:
        left, right = label_without_foil.rsplit(" - ", 1)
        team_name = right.strip() or None
        is_playerless = sticker_code == "00" or any(marker in label_without_foil.lower() for marker in SPECIAL_PLAYERLESS_MARKERS)
        player_name = None if is_playerless else left.strip() or None

    category_code, sticker_number = split_sticker_code(sticker_code)
    return {
        "sticker_code": sticker_code,
        "display_code": make_display_code(sticker_code),
        "category_code": category_code,
        "sticker_number": sticker_number,
        "label": label,
        "player_name": player_name,
        "team_name": team_name,
        "is_foil": is_foil,
        "is_team_photo": is_team_photo,
        "is_emblem": is_emblem,
        "raw_text": text,
        "source": "source_names.txt",
    }


def load_source_names(path: str | Path = "source_names.txt") -> list[dict]:
    source_path = Path(path)
    rows = []
    seen = set()
    for line_no, line in enumerate(source_path.read_text(encoding="utf-8").splitlines(), start=1):
        parsed = parse_source_name_line(line)
        if not parsed:
            continue
        if parsed["sticker_code"] in seen:
            raise ValueError(f"Code dupliqué dans {source_path}: {parsed['sticker_code']} ligne {line_no}")
        seen.add(parsed["sticker_code"])
        parsed["line_no"] = line_no
        rows.append(parsed)
    return rows


def _candidate_codes(code: str) -> list[str]:
    normalized = normalize_sticker_code(code)
    return [normalized, *EQUIVALENT_CODES.get(normalized, [])]


def _create_equivalent_sticker_if_needed(session: Session, row: dict) -> Sticker | None:
    if row["sticker_code"] != "00":
        return None
    first_album_order = min((sticker.album_order for sticker in get_stickers(session)), default=1)
    sticker = Sticker(
        album_order=min(first_album_order - 1, 0),
        raw_category="FWC",
        category_code="FWC",
        category_name="FWC",
        sticker_number=0,
        sticker_code="FWC0",
        display_code="FWC-0",
        source=str(row.get("source") or "source_names.txt"),
    )
    session.add(sticker)
    session.flush()
    for person in session.scalars(select(Person)):
        session.add(Holding(person_id=person.id, sticker_id=sticker.id, quantity=0))
    session.flush()
    return sticker


def enrich_stickers_from_source_names(session: Session, path: str | Path = "source_names.txt") -> dict:
    source_path = Path(path)
    rows = load_source_names(source_path)
    by_code = {row["sticker_code"]: row for row in rows}
    db_stickers = get_stickers(session)
    db_codes = {sticker.sticker_code for sticker in db_stickers}
    updated = 0
    inserted = 0
    matched_db_codes = set()
    ignored_source_codes = []
    for row in rows:
        sticker = None
        for candidate_code in _candidate_codes(row["sticker_code"]):
            sticker = get_sticker_by_code(session, candidate_code)
            if sticker:
                break
        if not sticker:
            sticker = _create_equivalent_sticker_if_needed(session, row)
            if sticker:
                inserted += 1
            else:
                ignored_source_codes.append(row["sticker_code"])
                continue
        sticker.label = row["label"]
        sticker.player_name = row["player_name"]
        sticker.team_name = row["team_name"]
        sticker.is_foil = bool(row["is_foil"])
        sticker.is_team_photo = bool(row["is_team_photo"])
        sticker.is_emblem = bool(row["is_emblem"])
        sticker.source = str(source_path)
        updated += 1
        matched_db_codes.add(sticker.sticker_code)

    db_codes_without_source_name = sorted(db_codes - matched_db_codes)
    import_run = ImportRun(
        import_type=SOURCE_NAMES_IMPORT_TYPE,
        source_path=str(source_path),
        status="success",
        rows_read=len(rows),
        rows_inserted=inserted,
        rows_updated=updated,
        errors={
            "ignored_source_codes": ignored_source_codes,
            "db_codes_without_source_name": db_codes_without_source_name,
        },
    )
    session.add(import_run)
    session.flush()
    return {
        "import_id": import_run.id,
        "source_path": str(source_path),
        "rows_read": len(rows),
        "rows_inserted": inserted,
        "rows_updated": updated,
        "ignored_source_codes": ignored_source_codes,
        "db_codes_without_source_name": db_codes_without_source_name,
    }
