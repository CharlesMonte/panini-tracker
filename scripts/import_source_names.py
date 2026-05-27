from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.db import get_session, init_db
from src.services.source_names_import import enrich_stickers_from_source_names


if __name__ == "__main__":
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("source_names.txt")
    if not path.exists():
        raise SystemExit(f"File not found: {path}")
    init_db()
    with get_session() as session:
        result = enrich_stickers_from_source_names(session, path)
    print(result)
