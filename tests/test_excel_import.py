from __future__ import annotations

import pytest

openpyxl = pytest.importorskip("openpyxl")
from openpyxl import Workbook
from sqlalchemy import select

from src.models import Holding, Person, Sticker
from src.services.excel_import import import_excel, preview_excel


def test_excel_import_ignores_formulas_and_propagates_categories(session, tmp_path):
    workbook = Workbook()
    ws = workbook.active
    ws.title = "Album"
    ws.append(["Equipes", "Numéro", "Antoine", "François", "Ceux qui le cherchent"])
    ws.append(["MEX", 1, 2, None, '=TEXTJOIN(", ", TRUE, C2)'])
    ws.append([None, 2, None, 1, '=TEXTJOIN(", ", TRUE, C3)'])
    ws.merge_cells("A2:A3")
    path = tmp_path / "album.xlsx"
    workbook.save(path)

    preview = preview_excel(path)
    assert preview.sticker_count == 2
    assert preview.people_names == ["Antoine", "François"]

    result = import_excel(session, path)
    assert result["stickers"] == 2
    stickers = list(session.scalars(select(Sticker).order_by(Sticker.album_order)))
    people = list(session.scalars(select(Person).order_by(Person.display_order)))
    holdings = {(h.person_id, h.sticker_id): h.quantity for h in session.scalars(select(Holding))}

    assert [s.sticker_code for s in stickers] == ["MEX1", "MEX2"]
    assert [p.name for p in people] == ["Antoine", "François"]
    assert holdings[(people[0].id, stickers[0].id)] == 2
    assert holdings[(people[1].id, stickers[1].id)] == 1
