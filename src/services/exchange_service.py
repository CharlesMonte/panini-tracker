from __future__ import annotations

from datetime import datetime, timezone
from itertools import combinations
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.config import settings
from src.models import ActionLog, Holding, Person, Sticker, Trade, TradeLine
from src.repositories import get_or_create_holding, get_people, get_stickers
from src.utils.normalization import normalize_sticker_code


def _holdings_matrix(session: Session) -> dict[tuple[int, int], int]:
    return {(h.person_id, h.sticker_id): h.quantity for h in session.scalars(select(Holding))}


def _sticker_label(sticker: Sticker) -> str:
    return sticker.player_name or sticker.label or sticker.display_code or sticker.sticker_code


def get_possible_gifts(session: Session) -> list[dict]:
    people = get_people(session)
    stickers = get_stickers(session)
    quantities = _holdings_matrix(session)
    rows = []
    for giver in people:
        for receiver in people:
            if giver.id == receiver.id:
                continue
            for sticker in stickers:
                giver_qty = quantities.get((giver.id, sticker.id), 0)
                receiver_qty = quantities.get((receiver.id, sticker.id), 0)
                if giver_qty >= 2 and receiver_qty == 0:
                    rows.append(
                        {
                            "giver_id": giver.id,
                            "giver": giver.name,
                            "receiver_id": receiver.id,
                            "receiver": receiver.name,
                            "sticker_id": sticker.id,
                            "display_code": sticker.display_code,
                            "label": _sticker_label(sticker),
                            "category_code": sticker.category_code,
                            "giver_quantity": giver_qty,
                        }
                    )
    return rows


def get_tradeable_stickers_between(session: Session, giver_id: int, receiver_id: int) -> list[dict]:
    stickers = get_stickers(session)
    quantities = _holdings_matrix(session)
    rows = []
    for sticker in stickers:
        giver_qty = quantities.get((giver_id, sticker.id), 0)
        receiver_qty = quantities.get((receiver_id, sticker.id), 0)
        if giver_qty >= 2 and receiver_qty == 0:
            rows.append(
                {
                    "sticker_id": sticker.id,
                    "display_code": sticker.display_code,
                    "sticker_code": sticker.sticker_code,
                    "label": _sticker_label(sticker),
                    "team_name": sticker.team_name,
                    "category_code": sticker.category_code,
                    "category_name": sticker.category_name,
                    "giver_quantity": giver_qty,
                }
            )
    return rows


def _candidate_for_pair(
    person_a: Person,
    person_b: Person,
    stickers: list[Sticker],
    quantities: dict[tuple[int, int], int],
    limit: int | None = None,
) -> list[dict]:
    a_can_give = [
        sticker
        for sticker in stickers
        if quantities.get((person_a.id, sticker.id), 0) >= 2 and quantities.get((person_b.id, sticker.id), 0) == 0
    ]
    b_can_give = [
        sticker
        for sticker in stickers
        if quantities.get((person_b.id, sticker.id), 0) >= 2 and quantities.get((person_a.id, sticker.id), 0) == 0
    ]
    rows = []
    for sticker_a in a_can_give:
        for sticker_b in b_can_give:
            rows.append(
                {
                    "person_a_id": person_a.id,
                    "person_a": person_a.name,
                    "person_b_id": person_b.id,
                    "person_b": person_b.name,
                    "sticker_a_gives_id": sticker_a.id,
                    "sticker_b_gives_id": sticker_b.id,
                    "sticker_a_gives": sticker_a.display_code,
                    "sticker_b_gives": sticker_b.display_code,
                    "sticker_a_label": _sticker_label(sticker_a),
                    "sticker_b_label": _sticker_label(sticker_b),
                    "category_a": sticker_a.category_code,
                    "category_b": sticker_b.category_code,
                }
            )
            if limit is not None and len(rows) >= limit:
                return rows
    return rows


def get_equivalent_trade_candidates(
    session: Session,
    person_a_id: int | None = None,
    person_b_id: int | None = None,
    limit: int | None = None,
) -> list[dict]:
    people = get_people(session)
    stickers = get_stickers(session)
    quantities = _holdings_matrix(session)
    by_id = {person.id: person for person in people}
    pairs: list[tuple[Person, Person]] = []
    if person_a_id and person_b_id:
        if person_a_id != person_b_id and person_a_id in by_id and person_b_id in by_id:
            pairs = [(by_id[person_a_id], by_id[person_b_id])]
    elif person_a_id:
        pairs = [(by_id[person_a_id], person) for person in people if person.id != person_a_id and person_a_id in by_id]
    elif person_b_id:
        pairs = [(person, by_id[person_b_id]) for person in people if person.id != person_b_id and person_b_id in by_id]
    else:
        pairs = list(combinations(people, 2))

    rows: list[dict] = []
    for person_a, person_b in pairs:
        remaining = None if limit is None else max(limit - len(rows), 0)
        rows.extend(_candidate_for_pair(person_a, person_b, stickers, quantities, remaining))
        if limit is not None and len(rows) >= limit:
            rows = rows[:limit]
            break
    rows.sort(key=lambda row: (row["category_a"] == row["category_b"], row["person_a"], row["person_b"], row["sticker_a_gives"]))
    return rows


def get_sale_candidates(
    session: Session,
    seller_id: int | None = None,
    buyer_id: int | None = None,
    limit: int | None = None,
) -> list[dict]:
    people = get_people(session)
    stickers = get_stickers(session)
    quantities = _holdings_matrix(session)
    rows = []
    for sticker in stickers:
        sellers = [p for p in people if quantities.get((p.id, sticker.id), 0) >= 2]
        buyers = [p for p in people if quantities.get((p.id, sticker.id), 0) == 0]
        for seller in sellers:
            if seller_id and seller.id != seller_id:
                continue
            for buyer in buyers:
                if seller.id == buyer.id or (buyer_id and buyer.id != buyer_id):
                    continue
                qty = quantities.get((seller.id, sticker.id), 0)
                rows.append(
                    {
                        "seller_id": seller.id,
                        "seller": seller.name,
                        "buyer_id": buyer.id,
                        "buyer": buyer.name,
                        "sticker_id": sticker.id,
                        "display_code": sticker.display_code,
                        "label": _sticker_label(sticker),
                        "category_code": sticker.category_code,
                        "seller_quantity": qty,
                        "seller_keeps_after_sale": qty - 1,
                        "price": settings.sale_price,
                    }
                )
                if limit is not None and len(rows) >= limit:
                    return rows
    return rows


def get_opportunity_summaries(session: Session, limit: int = 4) -> tuple[list[dict], list[dict]]:
    people = get_people(session)
    stickers = get_stickers(session)
    quantities = _holdings_matrix(session)
    gift_counts: dict[tuple[int, int], int] = {}
    sale_counts: dict[tuple[int, int], int] = {}
    names = {person.id: person.name for person in people}
    for sticker in stickers:
        owners_with_double = [person for person in people if quantities.get((person.id, sticker.id), 0) >= 2]
        missing_people = [person for person in people if quantities.get((person.id, sticker.id), 0) == 0]
        for giver in owners_with_double:
            for receiver in missing_people:
                if giver.id == receiver.id:
                    continue
                key = (giver.id, receiver.id)
                gift_counts[key] = gift_counts.get(key, 0) + 1
                sale_counts[key] = sale_counts.get(key, 0) + 1

    exchange_rows = []
    for person_a, person_b in combinations(people, 2):
        a_can_give = gift_counts.get((person_a.id, person_b.id), 0)
        b_can_give = gift_counts.get((person_b.id, person_a.id), 0)
        max_trades = min(a_can_give, b_can_give)
        choice_count = a_can_give * b_can_give
        if max_trades <= 0:
            continue
        exchange_rows.append(
            {
                "person_a_id": person_a.id,
                "person_b_id": person_b.id,
                "person_a": person_a.name,
                "person_b": person_b.name,
                "a_can_give": a_can_give,
                "b_can_give": b_can_give,
                "count": max_trades,
                "choice_count": choice_count,
            }
        )
    exchange_rows = sorted(exchange_rows, key=lambda row: (row["count"], row["choice_count"]), reverse=True)[:limit]

    def sale_rows_from_counts(counts: dict[tuple[int, int], int]) -> list[dict]:
        rows = [
            {"from_id": from_id, "to_id": to_id, "from": names[from_id], "to": names[to_id], "count": count}
            for (from_id, to_id), count in counts.items()
            if count > 0
        ]
        return sorted(rows, key=lambda row: row["count"], reverse=True)[:limit]

    return exchange_rows, sale_rows_from_counts(sale_counts)


def apply_sale(
    session: Session,
    seller_id: int,
    buyer_id: int,
    sticker_id: int,
    actor_name: str | None = None,
    price: float | None = None,
    batch_id: str | None = None,
) -> None:
    if seller_id == buyer_id:
        raise ValueError("Une vente nécessite deux personnes différentes.")
    sale_price = settings.sale_price if price is None else price
    seller_holding = get_or_create_holding(session, seller_id, sticker_id)
    buyer_holding = get_or_create_holding(session, buyer_id, sticker_id)
    if seller_holding.quantity < 2:
        raise ValueError("La vente n'est plus valide: le vendeur n'a plus ce sticker en double.")
    if buyer_holding.quantity != 0:
        raise ValueError("La vente n'est plus valide: l'acheteur possède déjà ce sticker.")

    seller_old = seller_holding.quantity
    buyer_old = buyer_holding.quantity
    seller_holding.quantity -= 1
    buyer_holding.quantity += 1
    sale_id = str(uuid4())
    metadata = {
        "sale_id": sale_id,
        "seller_id": seller_id,
        "buyer_id": buyer_id,
        "sticker_id": sticker_id,
        "price": sale_price,
    }
    if batch_id:
        metadata["batch_id"] = batch_id
        metadata["batch_action"] = "sale_session"
    session.add_all(
        [
            ActionLog(
                action_type="apply_sale",
                actor_name=actor_name,
                person_id=seller_id,
                sticker_id=sticker_id,
                old_quantity=seller_old,
                new_quantity=seller_holding.quantity,
                delta=-1,
                log_metadata=metadata,
            ),
            ActionLog(
                action_type="apply_sale",
                actor_name=actor_name,
                person_id=buyer_id,
                sticker_id=sticker_id,
                old_quantity=buyer_old,
                new_quantity=buyer_holding.quantity,
                delta=1,
                log_metadata=metadata,
            ),
        ]
    )
    session.flush()


def apply_equivalent_trade(
    session: Session,
    person_a_id: int,
    person_b_id: int,
    sticker_from_a_id: int,
    sticker_from_b_id: int,
    actor_name: str | None = None,
    batch_id: str | None = None,
) -> Trade:
    if person_a_id == person_b_id:
        raise ValueError("Un échange nécessite deux personnes différentes.")

    a_gives = get_or_create_holding(session, person_a_id, sticker_from_a_id)
    b_receives = get_or_create_holding(session, person_b_id, sticker_from_a_id)
    b_gives = get_or_create_holding(session, person_b_id, sticker_from_b_id)
    a_receives = get_or_create_holding(session, person_a_id, sticker_from_b_id)

    if a_gives.quantity < 2 or b_receives.quantity != 0:
        raise ValueError("L'échange n'est plus valide pour la carte donnée par A.")
    if b_gives.quantity < 2 or a_receives.quantity != 0:
        raise ValueError("L'échange n'est plus valide pour la carte donnée par B.")

    before = {
        (person_a_id, sticker_from_a_id): a_gives.quantity,
        (person_b_id, sticker_from_a_id): b_receives.quantity,
        (person_b_id, sticker_from_b_id): b_gives.quantity,
        (person_a_id, sticker_from_b_id): a_receives.quantity,
    }

    a_gives.quantity -= 1
    b_receives.quantity += 1
    b_gives.quantity -= 1
    a_receives.quantity += 1

    trade = Trade(
        status="applied",
        trade_type="equivalent_trade",
        person_a_id=person_a_id,
        person_b_id=person_b_id,
        created_by=actor_name,
        applied_by=actor_name,
        applied_at=datetime.now(timezone.utc),
        trade_metadata={
            "rule": "one_for_one_duplicate_for_missing",
            **({"batch_id": batch_id, "batch_action": "trade_session"} if batch_id else {}),
        },
    )
    session.add(trade)
    session.flush()
    session.add_all(
        [
            TradeLine(
                trade_id=trade.id,
                giver_person_id=person_a_id,
                receiver_person_id=person_b_id,
                sticker_id=sticker_from_a_id,
                quantity=1,
            ),
            TradeLine(
                trade_id=trade.id,
                giver_person_id=person_b_id,
                receiver_person_id=person_a_id,
                sticker_id=sticker_from_b_id,
                quantity=1,
            ),
        ]
    )
    for holding in [a_gives, b_receives, b_gives, a_receives]:
        old_qty = before[(holding.person_id, holding.sticker_id)]
        session.add(
            ActionLog(
                action_type="apply_trade",
                actor_name=actor_name,
                person_id=holding.person_id,
                sticker_id=holding.sticker_id,
                old_quantity=old_qty,
                new_quantity=holding.quantity,
                delta=holding.quantity - old_qty,
                log_metadata={
                    "trade_id": trade.id,
                    **({"batch_id": batch_id, "batch_action": "trade_session"} if batch_id else {}),
                },
            )
        )
    session.flush()
    return trade


def _parse_code_lines(raw_codes: str) -> list[str]:
    return [normalize_sticker_code(line.strip()) for line in raw_codes.splitlines() if normalize_sticker_code(line.strip())]


def _preview_trade_side(session: Session, giver_id: int, receiver_id: int, raw_codes: str) -> list[dict]:
    tradeable = {row["sticker_code"]: row for row in get_tradeable_stickers_between(session, giver_id, receiver_id)}
    codes = _parse_code_lines(raw_codes)
    seen: set[str] = set()
    items = []
    for code in codes:
        row = tradeable.get(code)
        status = "valid"
        message = "OK"
        if code in seen:
            status = "invalid"
            message = "Code en doublon dans cette liste"
        elif row is None:
            status = "invalid"
            message = "Le donneur n'a pas ce sticker en double ou le receveur le possède déjà"
        seen.add(code)
        item = {"code": code, "status": status, "message": message}
        if row:
            item.update(row)
        items.append(item)
    return items


def preview_batch_equivalent_trades(
    session: Session,
    person_a_id: int,
    person_b_id: int,
    raw_codes_from_a: str,
    raw_codes_from_b: str,
) -> dict:
    """Preview a multi-line 1-for-1 trade session between two people."""
    a_items = _preview_trade_side(session, person_a_id, person_b_id, raw_codes_from_a)
    b_items = _preview_trade_side(session, person_b_id, person_a_id, raw_codes_from_b)
    a_valid = [item for item in a_items if item["status"] == "valid"]
    b_valid = [item for item in b_items if item["status"] == "valid"]
    errors = []
    errors.extend(f"{item['code']}: {item['message']}" for item in a_items if item["status"] != "valid")
    errors.extend(f"{item['code']}: {item['message']}" for item in b_items if item["status"] != "valid")
    if len(a_valid) != len(b_valid):
        errors.append("Les deux listes doivent contenir le même nombre de stickers valides.")
    pairs = [
        {"from_a": item_a, "from_b": item_b}
        for item_a, item_b in zip(a_valid, b_valid)
    ]
    return {
        "a_items": a_items,
        "b_items": b_items,
        "pairs": pairs,
        "valid_trade_count": len(pairs) if not errors else 0,
        "errors": errors,
        "can_apply": bool(pairs) and not errors,
    }


def apply_batch_equivalent_trades(
    session: Session,
    person_a_id: int,
    person_b_id: int,
    pairs: list[dict],
    actor_name: str | None = None,
) -> dict:
    if not pairs:
        raise ValueError("Aucun échange valide à appliquer.")
    batch_id = str(uuid4())
    trades = []
    for pair in pairs:
        trades.append(
            apply_equivalent_trade(
                session,
                person_a_id,
                person_b_id,
                int(pair["from_a"]["sticker_id"]),
                int(pair["from_b"]["sticker_id"]),
                actor_name=actor_name,
                batch_id=batch_id,
            )
        )
    return {"batch_id": batch_id, "trade_count": len(trades)}


def preview_batch_sales(session: Session, seller_id: int, buyer_id: int, raw_codes: str) -> dict:
    sellable = {row["display_code"].replace("-", ""): row for row in get_sale_candidates(session, seller_id, buyer_id)}
    sellable.update({row["display_code"]: row for row in get_sale_candidates(session, seller_id, buyer_id)})
    codes = _parse_code_lines(raw_codes)
    seen: set[str] = set()
    items = []
    errors = []
    for code in codes:
        row = sellable.get(code)
        status = "valid"
        message = "OK"
        if code in seen:
            status = "invalid"
            message = "Code en doublon dans cette vente"
        elif row is None:
            status = "invalid"
            message = "Le vendeur n'a pas ce sticker en double ou l'acheteur le possède déjà"
        seen.add(code)
        item = {"code": code, "status": status, "message": message}
        if row:
            item.update(row)
        items.append(item)
        if status != "valid":
            errors.append(f"{code}: {message}")
    valid_items = [item for item in items if item["status"] == "valid"]
    return {
        "items": items,
        "valid_items": valid_items,
        "valid_sale_count": len(valid_items) if not errors else 0,
        "total_price": sum(float(item["price"]) for item in valid_items) if not errors else 0,
        "errors": errors,
        "can_apply": bool(valid_items) and not errors,
    }


def apply_batch_sales(
    session: Session,
    seller_id: int,
    buyer_id: int,
    items: list[dict],
    actor_name: str | None = None,
) -> dict:
    valid_items = [item for item in items if item.get("status") == "valid"]
    if not valid_items:
        raise ValueError("Aucune vente valide à appliquer.")
    batch_id = str(uuid4())
    for item in valid_items:
        apply_sale(
            session,
            seller_id=seller_id,
            buyer_id=buyer_id,
            sticker_id=int(item["sticker_id"]),
            actor_name=actor_name,
            price=float(item["price"]),
            batch_id=batch_id,
        )
    return {
        "batch_id": batch_id,
        "sale_count": len(valid_items),
        "total_price": sum(float(item["price"]) for item in valid_items),
    }
