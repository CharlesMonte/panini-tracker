from __future__ import annotations

from pathlib import Path

import pandas as pd
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.models import ActionLog, Holding, Person, Sticker
from src.repositories import get_people, get_stickers
from src.services.collection_service import get_collection_rows
from src.services.exchange_service import get_equivalent_trade_candidates, get_sale_candidates


def get_collection_matrix(session: Session) -> pd.DataFrame:
    people = get_people(session)
    stickers = get_stickers(session)
    quantities = {(h.person_id, h.sticker_id): h.quantity for h in session.scalars(select(Holding))}
    rows = []
    for sticker in stickers:
        row = {
            "category": sticker.raw_category,
            "display_code": sticker.display_code,
            "sticker_code": sticker.sticker_code,
            "player_name": sticker.player_name,
            "team_name": sticker.team_name,
            "label": sticker.label,
        }
        for person in people:
            row[person.name] = quantities.get((person.id, sticker.id), 0)
        rows.append(row)
    return pd.DataFrame(rows)


def get_missing_matrix(session: Session) -> pd.DataFrame:
    rows = []
    for person in get_people(session):
        for row in get_collection_rows(session, person.id, "Manquants"):
            rows.append({"person": person.name, **row})
    return pd.DataFrame(rows)


def get_duplicates_matrix(session: Session) -> pd.DataFrame:
    rows = []
    for person in get_people(session):
        for row in get_collection_rows(session, person.id, "Doubles"):
            rows.append({"person": person.name, **row})
    return pd.DataFrame(rows)


def get_history_dataframe(session: Session, limit: int | None = None) -> pd.DataFrame:
    stmt = (
        select(ActionLog, Person.name, Sticker.display_code)
        .join(Person, ActionLog.person_id == Person.id, isouter=True)
        .join(Sticker, ActionLog.sticker_id == Sticker.id, isouter=True)
        .order_by(ActionLog.created_at.desc())
    )
    if limit:
        stmt = stmt.limit(limit)
    rows = []
    for log, person_name, display_code in session.execute(stmt):
        rows.append(
            {
                "created_at": log.created_at,
                "action_type": log.action_type,
                "actor_name": log.actor_name,
                "person": person_name,
                "sticker": display_code,
                "old_quantity": log.old_quantity,
                "new_quantity": log.new_quantity,
                "delta": log.delta,
                "metadata": log.log_metadata,
            }
        )
    return pd.DataFrame(rows)


def export_csv(session: Session, output_path: str | Path) -> Path:
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    get_collection_matrix(session).to_csv(output_path, index=False)
    return output_path


def export_excel(session: Session, output_path: str | Path) -> Path:
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
        get_collection_matrix(session).to_excel(writer, "holdings_matrix", index=False)
        get_missing_matrix(session).to_excel(writer, "missing", index=False)
        get_duplicates_matrix(session).to_excel(writer, "duplicates", index=False)
        pd.DataFrame(get_equivalent_trade_candidates(session)).to_excel(writer, "equivalent_trades", index=False)
        pd.DataFrame(get_sale_candidates(session)).to_excel(writer, "sale_candidates", index=False)
        get_history_dataframe(session).to_excel(writer, "history", index=False)
    return output_path

