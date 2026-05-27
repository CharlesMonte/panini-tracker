from __future__ import annotations

from sqlalchemy import delete, func, or_, select
from sqlalchemy.orm import Session

from src.models import ActionLog, Holding, ImportRun, Person, Sticker, Trade, TradeLine
from src.repositories import get_or_create_holding, upsert_person
from src.utils.normalization import make_display_code, normalize_person_name, normalize_search_text, normalize_sticker_code, split_sticker_code


def get_database_overview(session: Session) -> dict:
    people_total = session.scalar(select(func.count()).select_from(Person)) or 0
    people_active = session.scalar(select(func.count()).select_from(Person).where(Person.active.is_(True))) or 0
    stickers_total = session.scalar(select(func.count()).select_from(Sticker)) or 0
    holdings_total = session.scalar(select(func.count()).select_from(Holding)) or 0
    holdings_nonzero = session.scalar(select(func.count()).select_from(Holding).where(Holding.quantity > 0)) or 0
    total_copies = int(session.scalar(select(func.coalesce(func.sum(Holding.quantity), 0))) or 0)
    expected_holdings = people_total * stickers_total
    return {
        "people_total": people_total,
        "people_active": people_active,
        "people_inactive": people_total - people_active,
        "stickers_total": stickers_total,
        "holdings_total": holdings_total,
        "holdings_missing_rows": max(expected_holdings - holdings_total, 0),
        "holdings_nonzero": holdings_nonzero,
        "total_copies": total_copies,
        "trades": session.scalar(select(func.count()).select_from(Trade)) or 0,
        "trade_lines": session.scalar(select(func.count()).select_from(TradeLine)) or 0,
        "actions": session.scalar(select(func.count()).select_from(ActionLog)) or 0,
        "imports": session.scalar(select(func.count()).select_from(ImportRun)) or 0,
    }


def get_category_admin_rows(session: Session) -> list[dict]:
    rows = []
    stmt = (
        select(
            Sticker.category_code,
            Sticker.category_name,
            func.count(Sticker.id),
            func.min(Sticker.album_order),
            func.max(Sticker.album_order),
        )
        .group_by(Sticker.category_code, Sticker.category_name)
        .order_by(func.min(Sticker.album_order))
    )
    for category_code, category_name, count, first_order, last_order in session.execute(stmt):
        rows.append(
            {
                "category_code": category_code,
                "category_name": category_name,
                "stickers": count,
                "first_album_order": first_order,
                "last_album_order": last_order,
            }
        )
    return rows


def get_people_admin_rows(session: Session) -> list[dict]:
    people = list(session.scalars(select(Person).order_by(Person.active.desc(), Person.display_order, Person.name)))
    rows = []
    for person in people:
        holding_count = session.scalar(select(func.count()).select_from(Holding).where(Holding.person_id == person.id)) or 0
        total_quantity = session.scalar(select(func.coalesce(func.sum(Holding.quantity), 0)).where(Holding.person_id == person.id)) or 0
        trade_count = (
            session.scalar(
                select(func.count())
                .select_from(Trade)
                .where(or_(Trade.person_a_id == person.id, Trade.person_b_id == person.id))
            )
            or 0
        )
        trade_line_count = (
            session.scalar(
                select(func.count())
                .select_from(TradeLine)
                .where(or_(TradeLine.giver_person_id == person.id, TradeLine.receiver_person_id == person.id))
            )
            or 0
        )
        rows.append(
            {
                "id": person.id,
                "name": person.name,
                "display_order": person.display_order,
                "active": person.active,
                "holdings": holding_count,
                "total_quantity": int(total_quantity),
                "trades": trade_count,
                "trade_lines": trade_line_count,
            }
        )
    return rows


def get_sticker_admin_rows(session: Session, query: str = "", category: str | None = None, limit: int = 500) -> list[dict]:
    stickers = list(session.scalars(select(Sticker).order_by(Sticker.album_order, Sticker.id)))
    needle = normalize_search_text(query)
    rows = []
    for sticker in stickers:
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
        holdings = session.scalar(select(func.count()).select_from(Holding).where(Holding.sticker_id == sticker.id)) or 0
        total_quantity = int(
            session.scalar(select(func.coalesce(func.sum(Holding.quantity), 0)).where(Holding.sticker_id == sticker.id)) or 0
        )
        rows.append(
            {
                "id": sticker.id,
                "album_order": sticker.album_order,
                "sticker_code": sticker.sticker_code,
                "display_code": sticker.display_code,
                "category_code": sticker.category_code,
                "category_name": sticker.category_name,
                "player_name": sticker.player_name,
                "team_name": sticker.team_name,
                "label": sticker.label,
                "is_foil": sticker.is_foil,
                "is_team_photo": sticker.is_team_photo,
                "is_emblem": sticker.is_emblem,
                "holdings": holdings,
                "total_quantity": total_quantity,
            }
        )
        if len(rows) >= limit:
            break
    return rows


def update_sticker_metadata(
    session: Session,
    sticker_id: int,
    *,
    sticker_code: str,
    album_order: int,
    category_code: str | None,
    category_name: str | None,
    player_name: str | None,
    team_name: str | None,
    label: str | None,
    is_foil: bool,
    is_team_photo: bool,
    is_emblem: bool,
    actor_name: str | None = None,
) -> Sticker:
    sticker = session.get(Sticker, sticker_id)
    if sticker is None:
        raise ValueError("Sticker introuvable.")
    normalized_code = normalize_sticker_code(sticker_code)
    if not normalized_code:
        raise ValueError("Le code sticker ne peut pas être vide.")
    existing = session.scalar(select(Sticker).where(Sticker.sticker_code == normalized_code, Sticker.id != sticker_id))
    if existing:
        raise ValueError(f"Le code {normalized_code} existe déjà.")
    old_values = {
        "sticker_code": sticker.sticker_code,
        "album_order": sticker.album_order,
        "category_code": sticker.category_code,
        "category_name": sticker.category_name,
        "player_name": sticker.player_name,
        "team_name": sticker.team_name,
        "label": sticker.label,
        "is_foil": sticker.is_foil,
        "is_team_photo": sticker.is_team_photo,
        "is_emblem": sticker.is_emblem,
    }
    split_category, sticker_number = split_sticker_code(normalized_code)
    sticker.sticker_code = normalized_code
    sticker.display_code = make_display_code(normalized_code)
    sticker.album_order = int(album_order)
    sticker.category_code = category_code or split_category
    sticker.category_name = category_name or category_code or split_category
    sticker.sticker_number = sticker_number
    sticker.player_name = player_name or None
    sticker.team_name = team_name or None
    sticker.label = label or None
    sticker.is_foil = is_foil
    sticker.is_team_photo = is_team_photo
    sticker.is_emblem = is_emblem
    session.add(
        ActionLog(
            action_type="manual_update",
            actor_name=actor_name,
            sticker_id=sticker.id,
            log_metadata={
                "admin_action": "update_sticker_metadata",
                "old_values": old_values,
                "new_code": sticker.sticker_code,
            },
        )
    )
    session.flush()
    return sticker


def delete_sticker(session: Session, sticker_id: int, confirm_code: str, actor_name: str | None = None) -> str:
    sticker = session.get(Sticker, sticker_id)
    if sticker is None:
        raise ValueError("Sticker introuvable.")
    if normalize_sticker_code(confirm_code) != sticker.sticker_code:
        raise ValueError("Le code de confirmation ne correspond pas.")
    sticker_code = sticker.sticker_code
    metadata = {
        "admin_action": "delete_sticker",
        "sticker_id": sticker.id,
        "sticker_code": sticker.sticker_code,
        "holdings": session.scalar(select(func.count()).select_from(Holding).where(Holding.sticker_id == sticker.id)) or 0,
        "total_quantity": int(
            session.scalar(select(func.coalesce(func.sum(Holding.quantity), 0)).where(Holding.sticker_id == sticker.id))
            or 0
        ),
    }
    session.add(
        ActionLog(
            action_type="manual_update",
            actor_name=actor_name,
            sticker_id=sticker.id,
            log_metadata=metadata,
        )
    )
    session.delete(sticker)
    session.flush()
    return sticker_code


def create_person(session: Session, name: str, display_order: int | None = None, actor_name: str | None = None) -> Person:
    normalized = normalize_person_name(name)
    if not normalized:
        raise ValueError("Le nom ne peut pas être vide.")
    if display_order is None:
        display_order = (session.scalar(select(func.coalesce(func.max(Person.display_order), 0))) or 0) + 1
    person = upsert_person(session, normalized, display_order)
    for sticker_id in session.scalars(select(Sticker.id)):
        get_or_create_holding(session, person.id, sticker_id)
    session.add(
        ActionLog(
            action_type="manual_update",
            actor_name=actor_name,
            person_id=person.id,
            log_metadata={"admin_action": "create_person", "person_name": person.name},
        )
    )
    session.flush()
    return person


def set_person_active(session: Session, person_id: int, active: bool, actor_name: str | None = None) -> Person:
    person = session.get(Person, person_id)
    if person is None:
        raise ValueError("Personne introuvable.")
    old_active = person.active
    person.active = active
    session.add(
        ActionLog(
            action_type="manual_update",
            actor_name=actor_name,
            person_id=person.id,
            log_metadata={
                "admin_action": "set_person_active",
                "person_name": person.name,
                "old_active": old_active,
                "new_active": active,
            },
        )
    )
    session.flush()
    return person


def update_person_display_order(
    session: Session, person_id: int, display_order: int, actor_name: str | None = None
) -> Person:
    person = session.get(Person, person_id)
    if person is None:
        raise ValueError("Personne introuvable.")
    old_order = person.display_order
    person.display_order = display_order
    session.add(
        ActionLog(
            action_type="manual_update",
            actor_name=actor_name,
            person_id=person.id,
            log_metadata={
                "admin_action": "update_person_display_order",
                "person_name": person.name,
                "old_display_order": old_order,
                "new_display_order": display_order,
            },
        )
    )
    session.flush()
    return person


def delete_person(session: Session, person_id: int, confirm_name: str, actor_name: str | None = None) -> str:
    person = session.get(Person, person_id)
    if person is None:
        raise ValueError("Personne introuvable.")
    if normalize_person_name(confirm_name) != person.name:
        raise ValueError("Le nom de confirmation ne correspond pas.")
    person_name = person.name
    metadata = {
        "admin_action": "delete_person",
        "person_id": person.id,
        "person_name": person.name,
        "holdings": session.scalar(select(func.count()).select_from(Holding).where(Holding.person_id == person.id)) or 0,
        "total_quantity": int(
            session.scalar(select(func.coalesce(func.sum(Holding.quantity), 0)).where(Holding.person_id == person.id))
            or 0
        ),
    }
    session.add(
        ActionLog(
            action_type="manual_update",
            actor_name=actor_name,
            person_id=person.id,
            log_metadata=metadata,
        )
    )
    session.delete(person)
    session.flush()
    return person_name


def ensure_full_holdings_matrix(session: Session, include_inactive: bool = True, actor_name: str | None = None) -> dict:
    people_stmt = select(Person)
    if not include_inactive:
        people_stmt = people_stmt.where(Person.active.is_(True))
    people_ids = list(session.scalars(people_stmt))
    sticker_ids = list(session.scalars(select(Sticker.id)))
    created = 0
    for person in people_ids:
        for sticker_id in sticker_ids:
            existing = session.scalar(
                select(Holding.id).where(Holding.person_id == person.id, Holding.sticker_id == sticker_id)
            )
            if existing is None:
                session.add(Holding(person_id=person.id, sticker_id=sticker_id, quantity=0))
                created += 1
    session.add(
        ActionLog(
            action_type="manual_update",
            actor_name=actor_name,
            log_metadata={
                "admin_action": "ensure_full_holdings_matrix",
                "include_inactive": include_inactive,
                "created_holdings": created,
            },
        )
    )
    session.flush()
    return {"created_holdings": created, "people": len(people_ids), "stickers": len(sticker_ids)}


def get_import_admin_rows(session: Session, limit: int = 100) -> list[dict]:
    rows = []
    stmt = select(ImportRun).order_by(ImportRun.created_at.desc()).limit(limit)
    for item in session.scalars(stmt):
        rows.append(
            {
                "id": item.id,
                "created_at": item.created_at,
                "import_type": item.import_type,
                "source_path": item.source_path,
                "status": item.status,
                "rows_read": item.rows_read,
                "rows_inserted": item.rows_inserted,
                "rows_updated": item.rows_updated,
                "errors": item.errors,
            }
        )
    return rows


def get_action_type_rows(session: Session) -> list[dict]:
    rows = []
    stmt = (
        select(ActionLog.action_type, func.count(ActionLog.id), func.max(ActionLog.created_at))
        .group_by(ActionLog.action_type)
        .order_by(func.count(ActionLog.id).desc())
    )
    for action_type, count, last_seen in session.execute(stmt):
        rows.append({"action_type": action_type, "count": count, "last_seen": last_seen})
    return rows


def purge_import_runs(session: Session, confirm_text: str, actor_name: str | None = None) -> int:
    if confirm_text != "PURGE IMPORTS":
        raise ValueError('Tapez exactement "PURGE IMPORTS" pour confirmer.')
    count = session.scalar(select(func.count()).select_from(ImportRun)) or 0
    session.execute(delete(ImportRun))
    session.add(
        ActionLog(
            action_type="manual_update",
            actor_name=actor_name,
            log_metadata={"admin_action": "purge_import_runs", "deleted_imports": count},
        )
    )
    session.flush()
    return count


def purge_action_log(session: Session, confirm_text: str) -> int:
    if confirm_text != "PURGE HISTORY":
        raise ValueError('Tapez exactement "PURGE HISTORY" pour confirmer.')
    count = session.scalar(select(func.count()).select_from(ActionLog)) or 0
    session.execute(delete(ActionLog))
    session.flush()
    return count
