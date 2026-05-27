from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.models import ActionLog, Holding, Person, Sticker
from src.repositories import get_or_create_holding


UNDOABLE_ACTIONS = {"add_sticker", "remove_sticker", "manual_update", "apply_sale"}
ACTION_LABELS = {
    "add_sticker": "Ajout",
    "remove_sticker": "Retrait",
    "manual_update": "Mise à jour",
    "apply_sale": "Vente",
    "apply_trade": "Échange",
    "undo": "Annulation",
    "import_excel": "Import Excel",
    "source_names_txt": "Import noms",
}


def human_action_label(action_type: str | None) -> str:
    return ACTION_LABELS.get(action_type or "", action_type or "")


def _undo_metadata_values(session: Session, key: str) -> set:
    values = set()
    for log in session.scalars(select(ActionLog).where(ActionLog.action_type == "undo")):
        metadata = log.log_metadata or {}
        if key in metadata:
            values.add(metadata[key])
    return values


def _is_action_undone(session: Session, action: ActionLog) -> bool:
    if action.action_type == "apply_sale":
        sale_id = (action.log_metadata or {}).get("sale_id")
        if sale_id:
            return sale_id in _undo_metadata_values(session, "undo_sale_id")
    batch_id = (action.log_metadata or {}).get("batch_id")
    if batch_id and batch_id in _undo_metadata_values(session, "undo_batch_id"):
        return True
    return action.id in _undo_metadata_values(session, "undo_of_action_id")


def can_undo_action(session: Session, action: ActionLog) -> bool:
    if action.action_type not in UNDOABLE_ACTIONS or action.action_type == "undo":
        return False
    if _is_action_undone(session, action):
        return False
    if action.person_id is None or action.sticker_id is None:
        return False
    if action.old_quantity is None:
        return False
    if action.action_type == "apply_sale":
        return bool((action.log_metadata or {}).get("sale_id"))
    return True


def undo_action(session: Session, action_id: int, actor_name: str | None = None) -> dict:
    action = session.get(ActionLog, action_id)
    if action is None:
        raise ValueError("Action introuvable.")
    if not can_undo_action(session, action):
        raise ValueError("Cette action ne peut pas être annulée.")
    if action.action_type == "apply_sale":
        return _undo_sale(session, action, actor_name)
    holding = get_or_create_holding(session, action.person_id, action.sticker_id)
    current_quantity = holding.quantity
    holding.quantity = int(action.old_quantity or 0)
    session.add(
        ActionLog(
            action_type="undo",
            actor_name=actor_name,
            person_id=action.person_id,
            sticker_id=action.sticker_id,
            old_quantity=current_quantity,
            new_quantity=holding.quantity,
            delta=holding.quantity - current_quantity,
            log_metadata={"undo_of_action_id": action.id, "undone_action_type": action.action_type},
        )
    )
    session.flush()
    return {"undone_action_id": action.id, "new_quantity": holding.quantity}


def can_undo_batch(session: Session, batch_id: str) -> bool:
    if not batch_id or batch_id in _undo_metadata_values(session, "undo_batch_id"):
        return False
    actions = _batch_actions(session, batch_id)
    return bool(actions) and all(can_undo_action(session, action) for action in actions)


def _batch_actions(session: Session, batch_id: str) -> list[ActionLog]:
    actions = list(session.scalars(select(ActionLog).where(ActionLog.action_type.in_(UNDOABLE_ACTIONS)).order_by(ActionLog.id)))
    return [action for action in actions if (action.log_metadata or {}).get("batch_id") == batch_id]


def undo_batch(session: Session, batch_id: str, actor_name: str | None = None) -> dict:
    if not can_undo_batch(session, batch_id):
        raise ValueError("Cette session ne peut pas être annulée.")
    actions = _batch_actions(session, batch_id)
    for action in actions:
        holding = get_or_create_holding(session, action.person_id, action.sticker_id)
        current_quantity = holding.quantity
        holding.quantity = int(action.old_quantity or 0)
        session.add(
            ActionLog(
                action_type="undo",
                actor_name=actor_name,
                person_id=action.person_id,
                sticker_id=action.sticker_id,
                old_quantity=current_quantity,
                new_quantity=holding.quantity,
                delta=holding.quantity - current_quantity,
                log_metadata={
                    "undo_of_action_id": action.id,
                    "undo_batch_id": batch_id,
                    "undone_action_type": action.action_type,
                },
            )
        )
    session.flush()
    return {"undo_batch_id": batch_id, "undone_lines": len(actions)}


def _undo_sale(session: Session, action: ActionLog, actor_name: str | None = None) -> dict:
    sale_id = (action.log_metadata or {}).get("sale_id")
    sale_logs = list(
        session.scalars(select(ActionLog).where(ActionLog.action_type == "apply_sale").order_by(ActionLog.id))
    )
    sale_logs = [log for log in sale_logs if (log.log_metadata or {}).get("sale_id") == sale_id]
    if len(sale_logs) != 2:
        raise ValueError("Cette vente ne peut pas être annulée automatiquement.")
    for log in sale_logs:
        holding = get_or_create_holding(session, log.person_id, log.sticker_id)
        current_quantity = holding.quantity
        holding.quantity = int(log.old_quantity or 0)
        session.add(
            ActionLog(
                action_type="undo",
                actor_name=actor_name,
                person_id=log.person_id,
                sticker_id=log.sticker_id,
                old_quantity=current_quantity,
                new_quantity=holding.quantity,
                delta=holding.quantity - current_quantity,
                log_metadata={"undo_of_action_id": log.id, "undo_sale_id": sale_id, "undone_action_type": "apply_sale"},
            )
        )
    session.flush()
    return {"undo_sale_id": sale_id, "undone_lines": len(sale_logs)}


def get_recent_actions(session: Session, limit: int = 20) -> list[dict]:
    stmt = (
        select(ActionLog, Person.name, Sticker.display_code, Sticker.player_name, Sticker.label)
        .join(Person, ActionLog.person_id == Person.id, isouter=True)
        .join(Sticker, ActionLog.sticker_id == Sticker.id, isouter=True)
        .order_by(ActionLog.created_at.desc(), ActionLog.id.desc())
        .limit(limit)
    )
    rows = []
    seen_sale_ids = set()
    for log, person_name, display_code, player_name, label in session.execute(stmt):
        sale_id = (log.log_metadata or {}).get("sale_id")
        if log.action_type == "apply_sale" and sale_id:
            if sale_id in seen_sale_ids:
                continue
            seen_sale_ids.add(sale_id)
        rows.append(
            {
                "id": log.id,
                "date": log.created_at,
                "action": log.action_type,
                "action_label": human_action_label(log.action_type),
                "personne": person_name,
                "sticker": display_code,
                "nom": player_name or label or display_code,
                "avant": log.old_quantity,
                "après": log.new_quantity,
                "delta": log.delta,
                "batch_id": (log.log_metadata or {}).get("batch_id"),
                "annulable": can_undo_action(session, log),
            }
        )
    return rows


def undo_last_simple_action(session: Session, actor_name: str | None = None) -> dict:
    for action in session.scalars(select(ActionLog).order_by(ActionLog.created_at.desc(), ActionLog.id.desc()).limit(50)):
        if can_undo_action(session, action):
            return undo_action(session, action.id, actor_name)
    raise ValueError("Aucune action récente annulable.")
