from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from src.models import Base, Holding, Person, Sticker


@pytest.fixture()
def session():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine, expire_on_commit=False, future=True)
    with Session() as session:
        yield session


def seed_trade_case(session):
    a = Person(name="A", display_order=1)
    b = Person(name="B", display_order=2)
    mex = Sticker(album_order=1, raw_category="MEX", category_code="MEX", category_name="MEX", sticker_number=1, sticker_code="MEX1", display_code="MEX-1")
    bra = Sticker(album_order=2, raw_category="BRA", category_code="BRA", category_name="BRA", sticker_number=1, sticker_code="BRA1", display_code="BRA-1")
    session.add_all([a, b, mex, bra])
    session.flush()
    return a, b, mex, bra


def add_holding(session, person, sticker, quantity):
    holding = Holding(person_id=person.id, sticker_id=sticker.id, quantity=quantity)
    session.add(holding)
    session.flush()
    return holding
