from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.models import Holding, Person, Sticker
from src.utils.normalization import normalize_person_name, normalize_sticker_code


def get_people(session: Session, active_only: bool = True) -> list[Person]:
    stmt = select(Person).order_by(Person.display_order, Person.name)
    if active_only:
        stmt = stmt.where(Person.active.is_(True))
    return list(session.scalars(stmt))


def get_stickers(session: Session) -> list[Sticker]:
    return list(session.scalars(select(Sticker).order_by(Sticker.album_order, Sticker.id)))


def get_person_by_name(session: Session, name: str) -> Person | None:
    normalized = normalize_person_name(name)
    return session.scalar(select(Person).where(Person.name == normalized))


def get_sticker_by_code(session: Session, code: str) -> Sticker | None:
    normalized = normalize_sticker_code(code)
    return session.scalar(select(Sticker).where(Sticker.sticker_code == normalized))


def upsert_person(session: Session, name: str, display_order: int = 0) -> Person:
    normalized = normalize_person_name(name)
    person = get_person_by_name(session, normalized)
    if person:
        person.display_order = display_order
        person.active = True
        return person
    person = Person(name=normalized, display_order=display_order, active=True)
    session.add(person)
    session.flush()
    return person


def upsert_sticker(session: Session, **values) -> tuple[Sticker, bool]:
    sticker = get_sticker_by_code(session, values["sticker_code"])
    created = sticker is None
    if sticker is None:
        sticker = Sticker(**values)
        session.add(sticker)
    else:
        for key, value in values.items():
            setattr(sticker, key, value)
    session.flush()
    return sticker, created


def get_or_create_holding(session: Session, person_id: int, sticker_id: int) -> Holding:
    holding = session.scalar(
        select(Holding).where(Holding.person_id == person_id, Holding.sticker_id == sticker_id)
    )
    if holding is None:
        holding = Holding(person_id=person_id, sticker_id=sticker_id, quantity=0)
        session.add(holding)
        session.flush()
    return holding

