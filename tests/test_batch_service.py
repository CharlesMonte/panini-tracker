from __future__ import annotations

from sqlalchemy import select

from conftest import add_holding, seed_trade_case
from src.models import ActionLog, Holding
from src.services.batch_service import apply_batch_add, preview_batch_add
from src.services.undo_service import undo_batch


def test_preview_batch_add_valid_unknown_duplicate_quantities(session):
    a, b, mex, bra = seed_trade_case(session)
    add_holding(session, a, mex, 1)
    add_holding(session, a, bra, 0)

    preview = preview_batch_add(session, a.id, "MEX1\nmex-1\nXXX9\nBRA1")

    assert preview["valid_count"] == 3
    assert preview["unknown_count"] == 1
    assert preview["duplicate_codes"] == ["MEX1"]
    mex_item = next(item for item in preview["valid_items"] if item["code"] == "MEX1")
    assert mex_item["current_quantity"] == 1
    assert mex_item["count_to_add"] == 2
    assert mex_item["new_quantity"] == 3


def test_apply_batch_add_uses_common_batch_id(session):
    a, b, mex, bra = seed_trade_case(session)
    add_holding(session, a, mex, 0)
    add_holding(session, a, bra, 1)
    preview = preview_batch_add(session, a.id, "MEX1\nBRA1")

    result = apply_batch_add(session, a.id, preview["items"], actor_name="Tester")

    assert result["added_count"] == 2
    assert result["updated_stickers"] == 2
    logs = list(session.scalars(select(ActionLog).where(ActionLog.action_type == "add_sticker")))
    assert len(logs) == 2
    assert {log.log_metadata["batch_id"] for log in logs} == {result["batch_id"]}


def test_undo_batch_restores_quantities_and_cannot_run_twice(session):
    a, b, mex, bra = seed_trade_case(session)
    add_holding(session, a, mex, 0)
    add_holding(session, a, bra, 1)
    preview = preview_batch_add(session, a.id, "MEX1\nBRA1\nBRA1")
    result = apply_batch_add(session, a.id, preview["items"], actor_name="Tester")

    undo_batch(session, result["batch_id"], actor_name="Tester")

    mex_qty = session.scalar(select(Holding.quantity).where(Holding.person_id == a.id, Holding.sticker_id == mex.id))
    bra_qty = session.scalar(select(Holding.quantity).where(Holding.person_id == a.id, Holding.sticker_id == bra.id))
    assert mex_qty == 0
    assert bra_qty == 1

    try:
        undo_batch(session, result["batch_id"], actor_name="Tester")
    except ValueError:
        pass
    else:
        raise AssertionError("undo_batch should not be possible twice")
