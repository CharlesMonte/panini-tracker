from __future__ import annotations

from sqlalchemy import select

from src.models import Holding, ImportRun, Person, Sticker
from src.services.source_names_import import enrich_stickers_from_source_names, parse_source_name_line


def test_parse_source_name_player_line():
    row = parse_source_name_line("MEX2 Luis Malagón - Mexico")
    assert row["sticker_code"] == "MEX2"
    assert row["player_name"] == "Luis Malagón"
    assert row["team_name"] == "Mexico"


def test_parse_source_name_team_logo_foil():
    row = parse_source_name_line("MEX1 Team Logo - Mexico FOIL")
    assert row["player_name"] is None
    assert row["team_name"] == "Mexico"
    assert row["is_foil"] is True
    assert row["is_emblem"] is True


def test_parse_source_name_team_photo():
    row = parse_source_name_line("MEX13 Team Photo - Mexico")
    assert row["is_team_photo"] is True
    assert row["player_name"] is None
    assert row["team_name"] == "Mexico"


def test_parse_source_name_fifa_museum_foil():
    row = parse_source_name_line("FWC9 Italy 1934 - FIFA Museum FOIL")
    assert row["player_name"] is None
    assert row["team_name"] == "FIFA Museum"
    assert row["is_foil"] is True


def test_parse_source_name_special_00():
    row = parse_source_name_line("00 Panini Logo FOIL")
    assert row["sticker_code"] == "00"
    assert row["player_name"] is None
    assert row["is_foil"] is True


def test_parse_source_name_known_aliases():
    assert parse_source_name_line("KAS12 Salem Al-Dawsari - Saudi Arabia")["sticker_code"] == "KSA12"
    assert parse_source_name_line("SWI9 Granit Xhaka - Switzerland")["sticker_code"] == "SUI9"


def test_enrich_stickers_from_source_names_updates_existing_only(session, tmp_path):
    sticker = Sticker(
        album_order=1,
        raw_category="MEX",
        category_code="MEX",
        category_name="MEX",
        sticker_number=2,
        sticker_code="MEX2",
        display_code="MEX-2",
    )
    session.add(sticker)
    session.flush()
    source_path = tmp_path / "source_names.txt"
    source_path.write_text("MEX2 Luis Malagón - Mexico\nBRA1 Team Logo - Brazil FOIL\n", encoding="utf-8")

    result = enrich_stickers_from_source_names(session, source_path)

    session.refresh(sticker)
    assert result["rows_read"] == 2
    assert result["rows_updated"] == 1
    assert result["ignored_source_codes"] == ["BRA1"]
    assert sticker.player_name == "Luis Malagón"
    assert sticker.team_name == "Mexico"
    assert session.scalar(select(ImportRun.import_type)) == "source_names_txt"


def test_enrich_source_00_matches_db_fwc0(session, tmp_path):
    sticker = Sticker(
        album_order=1,
        raw_category="FWC",
        category_code="FWC",
        category_name="FWC",
        sticker_number=0,
        sticker_code="FWC0",
        display_code="FWC-0",
    )
    session.add(sticker)
    session.flush()
    source_path = tmp_path / "source_names.txt"
    source_path.write_text("00 Panini Logo FOIL\n", encoding="utf-8")

    result = enrich_stickers_from_source_names(session, source_path)

    session.refresh(sticker)
    assert result["rows_updated"] == 1
    assert result["ignored_source_codes"] == []
    assert result["db_codes_without_source_name"] == []
    assert sticker.label == "Panini Logo FOIL"
    assert sticker.is_foil is True


def test_enrich_source_00_creates_fwc0_when_missing(session, tmp_path):
    person = Person(name="A", display_order=1)
    session.add(person)
    session.flush()
    source_path = tmp_path / "source_names.txt"
    source_path.write_text("00 Panini Logo FOIL\n", encoding="utf-8")

    result = enrich_stickers_from_source_names(session, source_path)

    sticker = session.scalar(select(Sticker).where(Sticker.sticker_code == "FWC0"))
    assert result["rows_inserted"] == 1
    assert result["rows_updated"] == 1
    assert result["ignored_source_codes"] == []
    assert sticker is not None
    assert sticker.label == "Panini Logo FOIL"
    assert session.scalar(select(Holding.quantity).where(Holding.person_id == person.id, Holding.sticker_id == sticker.id)) == 0
