from __future__ import annotations

from collections.abc import Generator
from contextlib import contextmanager

from sqlalchemy import create_engine, event
from sqlalchemy import text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from src.config import settings
from src.models import Base


def _engine_options() -> dict:
    if settings.database_url.startswith("postgresql"):
        return {"connect_args": {"options": "-c search_path=public"}}
    return {}


engine = create_engine(settings.database_url, pool_pre_ping=True, future=True, **_engine_options())
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False, future=True)


@event.listens_for(Engine, "connect")
def _set_sqlite_pragma(dbapi_connection, connection_record) -> None:
    if engine.url.get_backend_name().startswith("sqlite"):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


def init_db() -> None:
    if engine.url.get_backend_name().startswith("postgresql"):
        with engine.begin() as connection:
            connection.execute(text("SET search_path TO public"))
            Base.metadata.create_all(bind=connection)
        return
    Base.metadata.create_all(bind=engine)


@contextmanager
def get_session() -> Generator[Session, None, None]:
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
