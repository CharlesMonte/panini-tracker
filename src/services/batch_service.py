from __future__ import annotations

from collections import Counter
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.models import ActionLog, Holding, Sticker
from src.repositories import get_or_create_holding
from src.services.collection_service import _sticker_to_row
from src.utils.normalization import normalize_sticker_code


def _sticker_name(sticker: Sticker) -> str:
    return sticker.player_name or sticker.label or sticker.display_code or sticker.sticker_code


def preview_batch_add(session: Session, person_id: int, raw_codes: str) -> dict:
    """Parse a pasted list of codes and compute quantities before applying anything."""
    normalized_lines = []
    raw_by_code: dict[str, list[str]] = {}
    for raw_line in raw_codes.splitlines():
        raw = raw_line.strip()
        code = normalize_sticker_code(raw)
        if not code:
            continue
        normalized_lines.append(code)
        raw_by_code.setdefault(code, []).append(raw)

    counts = Counter(normalized_lines)
    if not counts:
        return {
            "items": [],
            "valid_items": [],
            "unknown_items": [],
            "duplicate_codes": [],
            "valid_count": 0,
            "unknown_count": 0,
            "unique_valid_count": 0,
        }

    stickers = {
        sticker.sticker_code: sticker
        for sticker in session.scalars(select(Sticker).where(Sticker.sticker_code.in_(list(counts.keys()))))
    }
    holdings = {
        holding.sticker_id: holding.quantity
        for holding in session.scalars(select(Holding).where(Holding.person_id == person_id))
    }

    items = []
    for code, count in counts.items():
        sticker = stickers.get(code)
        if sticker is None:
            items.append(
                {
                    "raw": raw_by_code[code][0],
                    "code": code,
                    "status": "unknown",
                    "message": "Code introuvable",
                    "count_to_add": count,
                    "duplicate_in_input": count > 1,
                    "current_quantity": None,
                    "new_quantity": None,
                }
            )
            continue
        current_quantity = holdings.get(sticker.id, 0)
        row = _sticker_to_row(sticker, current_quantity)
        row.update(
            {
                "raw": raw_by_code[code][0],
                "code": code,
                "status": "valid",
                "message": "OK",
                "count_to_add": count,
                "duplicate_in_input": count > 1,
                "current_quantity": current_quantity,
                "new_quantity": current_quantity + count,
                "sticker": _sticker_name(sticker),
            }
        )
        items.append(row)

    valid_items = [item for item in items if item["status"] == "valid"]
    unknown_items = [item for item in items if item["status"] == "unknown"]
    return {
        "items": items,
        "valid_items": valid_items,
        "unknown_items": unknown_items,
        "duplicate_codes": [code for code, count in counts.items() if count > 1],
        "valid_count": sum(item["count_to_add"] for item in valid_items),
        "unknown_count": sum(item["count_to_add"] for item in unknown_items),
        "unique_valid_count": len(valid_items),
    }


def apply_batch_add(
    session: Session,
    person_id: int,
    parsed_items: list[dict],
    actor_name: str | None = None,
) -> dict:
    """Apply a previewed batch as one logical session, logged with a shared batch_id."""
    valid_items = [item for item in parsed_items if item.get("status") == "valid" and item.get("count_to_add", 0) > 0]
    if not valid_items:
        raise ValueError("Aucun code valide à appliquer.")

    batch_id = str(uuid4())
    total_added = 0
    updated_stickers = 0
    for item in valid_items:
        sticker_id = int(item["sticker_id"])
        count_to_add = int(item["count_to_add"])
        holding = get_or_create_holding(session, person_id, sticker_id)
        old_quantity = holding.quantity
        holding.quantity = old_quantity + count_to_add
        total_added += count_to_add
        updated_stickers += 1
        session.add(
            ActionLog(
                action_type="add_sticker",
                actor_name=actor_name or None,
                person_id=person_id,
                sticker_id=sticker_id,
                old_quantity=old_quantity,
                new_quantity=holding.quantity,
                delta=count_to_add,
                log_metadata={
                    "batch_id": batch_id,
                    "batch_action": "quick_entry",
                    "count_to_add": count_to_add,
                },
            )
        )
    session.flush()
    return {
        "batch_id": batch_id,
        "added_count": total_added,
        "updated_stickers": updated_stickers,
    }
