from __future__ import annotations

import pytest
from sqlalchemy import select

from conftest import add_holding, seed_trade_case
from src.models import ActionLog, Holding
from src.services.collection_service import add_quantity
from src.services.exchange_service import apply_sale
from src.services.undo_service import human_action_label, undo_action


def _latest_action(session, action_type: str):
    return session.scalar(select(ActionLog).where(ActionLog.action_type == action_type).order_by(ActionLog.id.desc()))


def test_undo_add_sticker(session):
    a, b, mex, bra = seed_trade_case(session)
    add_holding(session, a, mex, 0)
    add_quantity(session, a.id, mex.id, 1, actor_name="Tester")
    action = _latest_action(session, "add_sticker")

    undo_action(session, action.id, actor_name="Tester")

    qty = session.scalar(select(Holding.quantity).where(Holding.person_id == a.id, Holding.sticker_id == mex.id))
    assert qty == 0


def test_undo_remove_sticker(session):
    a, b, mex, bra = seed_trade_case(session)
    add_holding(session, a, mex, 2)
    add_quantity(session, a.id, mex.id, -1, actor_name="Tester")
    action = _latest_action(session, "remove_sticker")

    undo_action(session, action.id, actor_name="Tester")

    qty = session.scalar(select(Holding.quantity).where(Holding.person_id == a.id, Holding.sticker_id == mex.id))
    assert qty == 2


def test_undo_sale(session):
    a, b, mex, bra = seed_trade_case(session)
    add_holding(session, a, mex, 3)
    add_holding(session, b, mex, 0)
    apply_sale(session, a.id, b.id, mex.id, actor_name="Tester")
    action = _latest_action(session, "apply_sale")

    undo_action(session, action.id, actor_name="Tester")

    seller_qty = session.scalar(select(Holding.quantity).where(Holding.person_id == a.id, Holding.sticker_id == mex.id))
    buyer_qty = session.scalar(select(Holding.quantity).where(Holding.person_id == b.id, Holding.sticker_id == mex.id))
    assert seller_qty == 3
    assert buyer_qty == 0


def test_cannot_undo_twice(session):
    a, b, mex, bra = seed_trade_case(session)
    add_holding(session, a, mex, 0)
    add_quantity(session, a.id, mex.id, 1, actor_name="Tester")
    action = _latest_action(session, "add_sticker")

    undo_action(session, action.id, actor_name="Tester")

    with pytest.raises(ValueError):
        undo_action(session, action.id, actor_name="Tester")


def test_human_action_labels():
    assert human_action_label("add_sticker") == "Ajout"
    assert human_action_label("remove_sticker") == "Retrait"
    assert human_action_label("apply_sale") == "Vente"
    assert human_action_label("apply_trade") == "Échange"
