from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def json_type():
    return JSON().with_variant(JSONB, "postgresql")


class Base(DeclarativeBase):
    pass


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class Person(Base, TimestampMixin):
    __tablename__ = "people"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    display_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    holdings: Mapped[list["Holding"]] = relationship(back_populates="person", cascade="all, delete-orphan")


class Sticker(Base, TimestampMixin):
    __tablename__ = "stickers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    album_order: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    raw_category: Mapped[Optional[str]] = mapped_column(Text)
    category_code: Mapped[Optional[str]] = mapped_column(Text, index=True)
    category_name: Mapped[Optional[str]] = mapped_column(Text)
    sticker_number: Mapped[Optional[int]] = mapped_column(Integer)
    sticker_code: Mapped[str] = mapped_column(Text, unique=True, nullable=False, index=True)
    display_code: Mapped[Optional[str]] = mapped_column(Text)
    player_name: Mapped[Optional[str]] = mapped_column(Text, index=True)
    team_name: Mapped[Optional[str]] = mapped_column(Text, index=True)
    label: Mapped[Optional[str]] = mapped_column(Text)
    is_foil: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_team_photo: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_emblem: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    source: Mapped[Optional[str]] = mapped_column(Text)

    holdings: Mapped[list["Holding"]] = relationship(back_populates="sticker", cascade="all, delete-orphan")


class Holding(Base, TimestampMixin):
    __tablename__ = "holdings"
    __table_args__ = (
        UniqueConstraint("person_id", "sticker_id", name="uq_holdings_person_sticker"),
        CheckConstraint("quantity >= 0", name="ck_holdings_quantity_non_negative"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    person_id: Mapped[int] = mapped_column(ForeignKey("people.id", ondelete="CASCADE"), nullable=False, index=True)
    sticker_id: Mapped[int] = mapped_column(ForeignKey("stickers.id", ondelete="CASCADE"), nullable=False, index=True)
    quantity: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    person: Mapped[Person] = relationship(back_populates="holdings")
    sticker: Mapped[Sticker] = relationship(back_populates="holdings")


class ActionLog(Base):
    __tablename__ = "action_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    action_type: Mapped[str] = mapped_column(Text, nullable=False, index=True)
    actor_name: Mapped[Optional[str]] = mapped_column(Text)
    person_id: Mapped[Optional[int]] = mapped_column(ForeignKey("people.id", ondelete="SET NULL"), index=True)
    sticker_id: Mapped[Optional[int]] = mapped_column(ForeignKey("stickers.id", ondelete="SET NULL"), index=True)
    old_quantity: Mapped[Optional[int]] = mapped_column(Integer)
    new_quantity: Mapped[Optional[int]] = mapped_column(Integer)
    delta: Mapped[Optional[int]] = mapped_column(Integer)
    log_metadata: Mapped[Optional[dict]] = mapped_column("metadata", json_type())
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)

    person: Mapped[Optional[Person]] = relationship(Person)
    sticker: Mapped[Optional[Sticker]] = relationship(Sticker)


class Trade(Base):
    __tablename__ = "trades"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    status: Mapped[str] = mapped_column(Text, nullable=False, default="proposed", index=True)
    trade_type: Mapped[str] = mapped_column(Text, nullable=False, default="equivalent_trade")
    person_a_id: Mapped[int] = mapped_column(ForeignKey("people.id", ondelete="CASCADE"), nullable=False)
    person_b_id: Mapped[int] = mapped_column(ForeignKey("people.id", ondelete="CASCADE"), nullable=False)
    created_by: Mapped[Optional[str]] = mapped_column(Text)
    applied_by: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    applied_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    trade_metadata: Mapped[Optional[dict]] = mapped_column("metadata", json_type())

    lines: Mapped[list["TradeLine"]] = relationship(back_populates="trade", cascade="all, delete-orphan")
    person_a: Mapped[Person] = relationship(Person, foreign_keys=[person_a_id])
    person_b: Mapped[Person] = relationship(Person, foreign_keys=[person_b_id])


class TradeLine(Base):
    __tablename__ = "trade_lines"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    trade_id: Mapped[int] = mapped_column(ForeignKey("trades.id", ondelete="CASCADE"), nullable=False, index=True)
    giver_person_id: Mapped[int] = mapped_column(ForeignKey("people.id", ondelete="CASCADE"), nullable=False)
    receiver_person_id: Mapped[int] = mapped_column(ForeignKey("people.id", ondelete="CASCADE"), nullable=False)
    sticker_id: Mapped[int] = mapped_column(ForeignKey("stickers.id", ondelete="CASCADE"), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    trade: Mapped[Trade] = relationship(back_populates="lines")
    giver: Mapped[Person] = relationship(Person, foreign_keys=[giver_person_id])
    receiver: Mapped[Person] = relationship(Person, foreign_keys=[receiver_person_id])
    sticker: Mapped[Sticker] = relationship(Sticker)


class ImportRun(Base):
    __tablename__ = "imports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    import_type: Mapped[str] = mapped_column(Text, nullable=False)
    source_path: Mapped[Optional[str]] = mapped_column(Text)
    status: Mapped[str] = mapped_column(Text, nullable=False)
    rows_read: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    rows_inserted: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    rows_updated: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    errors: Mapped[Optional[Any]] = mapped_column(json_type())
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
