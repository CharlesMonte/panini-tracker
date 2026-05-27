from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.db import engine, init_db
from src.models import Base


if __name__ == "__main__":
    Base.metadata.drop_all(bind=engine)
    init_db()
    print("Database reset.")
