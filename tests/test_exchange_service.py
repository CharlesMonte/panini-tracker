from __future__ import annotations

from src.models import Sticker
from sqlalchemy import select

from src.models import ActionLog, Holding
from src.services.exchange_service import (
    apply_batch_equivalent_trades,
    apply_batch_sales,
    apply_sale,
    get_equivalent_trade_candidates,
    get_opportunity_summaries,
    get_sale_candidates,
    get_tradeable_stickers_between,
    preview_batch_equivalent_trades,
    preview_batch_sales,
)
from conftest import add_holding, seed_trade_case


def test_equivalent_trade_candidate(session):
    a, b, mex, bra = seed_trade_case(session)
    add_holding(session, a, mex, 2)
    add_holding(session, a, bra, 0)
    add_holding(session, b, mex, 0)
    add_holding(session, b, bra, 2)

    rows = get_equivalent_trade_candidates(session, a.id, b.id)

    assert len(rows) == 1
    assert rows[0]["sticker_a_gives"] == "MEX-1"
    assert rows[0]["sticker_b_gives"] == "BRA-1"


def test_no_trade_if_not_duplicate(session):
    a, b, mex, bra = seed_trade_case(session)
    add_holding(session, a, mex, 1)
    add_holding(session, b, mex, 0)
    add_holding(session, b, bra, 2)

    rows = get_equivalent_trade_candidates(session, a.id, b.id)

    assert rows == []


def test_sale_candidate(session):
    a, b, mex, bra = seed_trade_case(session)
    add_holding(session, a, mex, 3)
    add_holding(session, b, mex, 0)

    rows = get_sale_candidates(session, a.id, b.id)

    assert len(rows) == 1
    assert rows[0]["seller"] == "A"
    assert rows[0]["buyer"] == "B"
    assert rows[0]["price"] == 0.22


def test_apply_sale_updates_quantities_and_logs(session):
    a, b, mex, bra = seed_trade_case(session)
    add_holding(session, a, mex, 3)
    add_holding(session, b, mex, 0)

    apply_sale(session, a.id, b.id, mex.id, actor_name="Tester", price=0.22)

    seller_qty = session.scalar(select(Holding.quantity).where(Holding.person_id == a.id, Holding.sticker_id == mex.id))
    buyer_qty = session.scalar(select(Holding.quantity).where(Holding.person_id == b.id, Holding.sticker_id == mex.id))
    logs = list(session.scalars(select(ActionLog).where(ActionLog.action_type == "apply_sale")))
    assert seller_qty == 2
    assert buyer_qty == 1
    assert len(logs) == 2
    assert logs[0].log_metadata["price"] == 0.22


def test_tradeable_stickers_between_only_duplicates_missing(session):
    a, b, mex, bra = seed_trade_case(session)
    fra = Sticker(
        album_order=3,
        raw_category="FRA",
        category_code="FRA",
        category_name="FRA",
        sticker_number=1,
        sticker_code="FRA1",
        display_code="FRA-1",
    )
    session.add(fra)
    session.flush()
    add_holding(session, a, mex, 2)
    add_holding(session, b, mex, 0)
    add_holding(session, a, bra, 1)
    add_holding(session, b, bra, 0)
    add_holding(session, a, fra, 2)
    add_holding(session, b, fra, 1)

    rows = get_tradeable_stickers_between(session, a.id, b.id)

    assert [row["display_code"] for row in rows] == ["MEX-1"]


def test_opportunity_summaries(session):
    a, b, mex, bra = seed_trade_case(session)
    fra = Sticker(
        album_order=3,
        raw_category="FRA",
        category_code="FRA",
        category_name="FRA",
        sticker_number=1,
        sticker_code="FRA1",
        display_code="FRA-1",
    )
    session.add(fra)
    session.flush()
    add_holding(session, a, mex, 2)
    add_holding(session, b, mex, 0)
    add_holding(session, a, bra, 0)
    add_holding(session, b, bra, 2)
    add_holding(session, a, fra, 0)
    add_holding(session, b, fra, 2)

    exchange_rows, sale_rows = get_opportunity_summaries(session)

    assert exchange_rows[0] == {
        "person_a_id": a.id,
        "person_b_id": b.id,
        "person_a": "A",
        "person_b": "B",
        "a_can_give": 1,
        "b_can_give": 2,
        "count": 1,
        "choice_count": 2,
    }
    assert {"from_id": a.id, "to_id": b.id, "from": "A", "to": "B", "count": 1} in sale_rows


def test_batch_trade_preview_and_apply(session):
    a, b, mex, bra = seed_trade_case(session)
    add_holding(session, a, mex, 2)
    add_holding(session, b, mex, 0)
    add_holding(session, a, bra, 0)
    add_holding(session, b, bra, 2)

    preview = preview_batch_equivalent_trades(session, a.id, b.id, "MEX1", "BRA1")

    assert preview["can_apply"] is True
    assert preview["valid_trade_count"] == 1

    result = apply_batch_equivalent_trades(session, a.id, b.id, preview["pairs"], actor_name="Tester")

    assert result["trade_count"] == 1
    assert session.scalar(select(Holding.quantity).where(Holding.person_id == a.id, Holding.sticker_id == mex.id)) == 1
    assert session.scalar(select(Holding.quantity).where(Holding.person_id == b.id, Holding.sticker_id == mex.id)) == 1
    assert session.scalar(select(Holding.quantity).where(Holding.person_id == a.id, Holding.sticker_id == bra.id)) == 1
    assert session.scalar(select(Holding.quantity).where(Holding.person_id == b.id, Holding.sticker_id == bra.id)) == 1


def test_batch_sales_preview_and_apply(session):
    a, b, mex, bra = seed_trade_case(session)
    add_holding(session, a, mex, 3)
    add_holding(session, b, mex, 0)
    add_holding(session, a, bra, 1)
    add_holding(session, b, bra, 0)

    preview = preview_batch_sales(session, a.id, b.id, "MEX1\nBRA1")

    assert preview["can_apply"] is False
    assert preview["valid_sale_count"] == 0
    assert preview["errors"] == ["BRA1: Le vendeur n'a pas ce sticker en double ou l'acheteur le possède déjà"]

    preview = preview_batch_sales(session, a.id, b.id, "MEX1")
    result = apply_batch_sales(session, a.id, b.id, preview["items"], actor_name="Tester")

    assert result["sale_count"] == 1
    assert result["total_price"] == 0.22
    assert session.scalar(select(Holding.quantity).where(Holding.person_id == a.id, Holding.sticker_id == mex.id)) == 2
    assert session.scalar(select(Holding.quantity).where(Holding.person_id == b.id, Holding.sticker_id == mex.id)) == 1
