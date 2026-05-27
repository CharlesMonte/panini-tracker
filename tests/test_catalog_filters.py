from __future__ import annotations

from src.services.collection_service import filter_stickers_by_kind, get_sticker_kind


def test_catalog_kind_filters():
    rows = [
        {"display_code": "A", "is_foil": False, "is_team_photo": False, "is_emblem": False},
        {"display_code": "B", "is_foil": True, "is_team_photo": False, "is_emblem": True},
        {"display_code": "C", "is_foil": False, "is_team_photo": True, "is_emblem": False},
    ]

    assert get_sticker_kind(rows[0]) == "Joueur"
    assert [row["display_code"] for row in filter_stickers_by_kind(rows, "Foil")] == ["B"]
    assert [row["display_code"] for row in filter_stickers_by_kind(rows, "Logo")] == ["B"]
    assert [row["display_code"] for row in filter_stickers_by_kind(rows, "Photo équipe")] == ["C"]
