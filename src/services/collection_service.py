from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.models import ActionLog, Holding, Person, Sticker
from src.repositories import get_or_create_holding, get_people, get_sticker_by_code, get_stickers
from src.utils.normalization import normalize_search_text


def get_person_stats(session: Session, person_id: int) -> dict:
    stickers = get_stickers(session)
    holdings = {
        h.sticker_id: h.quantity
        for h in session.scalars(select(Holding).where(Holding.person_id == person_id))
    }
    total_stickers = len(stickers)
    quantities = [holdings.get(sticker.id, 0) for sticker in stickers]
    owned_distinct = sum(1 for qty in quantities if qty > 0)
    total_copies = sum(quantities)
    duplicates = sum(max(qty - 1, 0) for qty in quantities)
    duplicate_rate = (duplicates / total_copies * 100) if total_copies else 0
    missing = total_stickers - owned_distinct
    completion = (owned_distinct / total_stickers * 100) if total_stickers else 0
    person = session.get(Person, person_id)
    return {
        "person_id": person_id,
        "person_name": person.name if person else "",
        "owned_distinct": owned_distinct,
        "total_copies": total_copies,
        "duplicates": duplicates,
        "duplicate_rate": duplicate_rate,
        "missing": missing,
        "total_stickers": total_stickers,
        "completion": completion,
    }


def get_all_people_stats(session: Session) -> list[dict]:
    people = get_people(session)
    stickers = get_stickers(session)
    total_stickers = len(stickers)
    quantities = {(h.person_id, h.sticker_id): h.quantity for h in session.scalars(select(Holding))}
    rows = []
    for person in people:
        person_quantities = [quantities.get((person.id, sticker.id), 0) for sticker in stickers]
        owned_distinct = sum(1 for qty in person_quantities if qty > 0)
        total_copies = sum(person_quantities)
        duplicates = sum(max(qty - 1, 0) for qty in person_quantities)
        rows.append(
            {
                "person_id": person.id,
                "person_name": person.name,
                "owned_distinct": owned_distinct,
                "total_copies": total_copies,
                "duplicates": duplicates,
                "duplicate_rate": (duplicates / total_copies * 100) if total_copies else 0,
                "missing": total_stickers - owned_distinct,
                "total_stickers": total_stickers,
                "completion": (owned_distinct / total_stickers * 100) if total_stickers else 0,
            }
        )
    return rows


def _sticker_to_row(sticker: Sticker, quantity: int = 0) -> dict:
    return {
        "sticker_id": sticker.id,
        "album_order": sticker.album_order,
        "display_code": sticker.display_code,
        "sticker_code": sticker.sticker_code,
        "category_code": sticker.category_code,
        "category_name": sticker.category_name,
        "player_name": sticker.player_name,
        "team_name": sticker.team_name,
        "label": sticker.label,
        "is_foil": sticker.is_foil,
        "is_team_photo": sticker.is_team_photo,
        "is_emblem": sticker.is_emblem,
        "quantity": quantity,
        "duplicate_count": max(quantity - 1, 0),
    }


def get_sticker_kind(row: dict) -> str:
    if row.get("is_team_photo"):
        return "Photo équipe"
    if row.get("is_emblem"):
        return "Logo"
    if row.get("is_foil"):
        return "Foil"
    return "Joueur"


def filter_stickers_by_kind(rows: list[dict], kind_filter: str) -> list[dict]:
    if kind_filter == "Tous":
        return rows
    if kind_filter == "Foil":
        return [row for row in rows if row.get("is_foil")]
    return [row for row in rows if get_sticker_kind(row) == kind_filter]


def get_collection_rows(session: Session, person_id: int, status: str = "Tous", category: str | None = None) -> list[dict]:
    holdings = {
        h.sticker_id: h.quantity
        for h in session.scalars(select(Holding).where(Holding.person_id == person_id))
    }
    rows = []
    for sticker in get_stickers(session):
        qty = holdings.get(sticker.id, 0)
        if category and sticker.category_code != category:
            continue
        if status == "Manquants" and qty != 0:
            continue
        if status == "Possédés" and qty <= 0:
            continue
        if status == "Doubles" and qty <= 1:
            continue
        rows.append(_sticker_to_row(sticker, qty))
    return rows


def get_missing(session: Session, person_id: int) -> list[dict]:
    return get_collection_rows(session, person_id, "Manquants")


def get_duplicates(session: Session, person_id: int) -> list[dict]:
    return get_collection_rows(session, person_id, "Doubles")


def get_owned(session: Session, person_id: int) -> list[dict]:
    return get_collection_rows(session, person_id, "Possédés")


def search_stickers(session: Session, query: str = "", category: str | None = None) -> list[dict]:
    needle = normalize_search_text(query)
    rows = []
    for sticker in get_stickers(session):
        if category and sticker.category_code != category:
            continue
        haystack = normalize_search_text(
            " ".join(
                [
                    sticker.sticker_code,
                    sticker.display_code or "",
                    sticker.category_code or "",
                    sticker.category_name or "",
                    sticker.player_name or "",
                    sticker.team_name or "",
                    sticker.label or "",
                ]
            )
        )
        if needle and needle not in haystack:
            continue
        rows.append(_sticker_to_row(sticker))
    return rows


def set_quantity(
    session: Session,
    person_id: int,
    sticker_id: int,
    quantity: int,
    actor_name: str | None = None,
    action_type: str = "manual_update",
) -> Holding:
    if quantity < 0:
        raise ValueError("La quantité ne peut pas être négative.")
    holding = get_or_create_holding(session, person_id, sticker_id)
    old_quantity = holding.quantity
    holding.quantity = int(quantity)
    session.add(
        ActionLog(
            action_type=action_type,
            actor_name=actor_name or None,
            person_id=person_id,
            sticker_id=sticker_id,
            old_quantity=old_quantity,
            new_quantity=holding.quantity,
            delta=holding.quantity - old_quantity,
        )
    )
    session.flush()
    return holding


def add_quantity(session: Session, person_id: int, sticker_id: int, delta: int, actor_name: str | None = None) -> Holding:
    holding = get_or_create_holding(session, person_id, sticker_id)
    new_quantity = holding.quantity + delta
    action_type = "add_sticker" if delta >= 0 else "remove_sticker"
    return set_quantity(session, person_id, sticker_id, new_quantity, actor_name, action_type)


def add_sticker(session: Session, person_id: int, sticker_code: str, actor_name: str | None = None) -> Holding:
    sticker = get_sticker_by_code(session, sticker_code)
    if sticker is None:
        raise ValueError(f"Sticker introuvable: {sticker_code}")
    return add_quantity(session, person_id, sticker.id, 1, actor_name)


def remove_sticker(session: Session, person_id: int, sticker_code: str, actor_name: str | None = None) -> Holding:
    sticker = get_sticker_by_code(session, sticker_code)
    if sticker is None:
        raise ValueError(f"Sticker introuvable: {sticker_code}")
    return add_quantity(session, person_id, sticker.id, -1, actor_name)
