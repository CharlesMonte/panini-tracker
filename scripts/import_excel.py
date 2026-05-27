from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.db import get_session, init_db
from src.services.import_service import run_excel_import


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("Usage: python scripts/import_excel.py data/input/mon_fichier.xlsx")
    path = Path(sys.argv[1])
    if not path.exists():
        raise SystemExit(f"File not found: {path}")
    init_db()
    with get_session() as session:
        result = run_excel_import(session, path)
    print(result)
