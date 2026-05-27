from __future__ import annotations

import pandas as pd
import streamlit as st

from src.db import get_session
from src.repositories import get_people, get_stickers
from src.services.collection_service import get_collection_rows, get_person_stats
from src.services.exchange_service import get_sale_candidates, get_tradeable_stickers_between
from src.ui.components import ensure_db, render_empty_import_hint
from src.utils.normalization import normalize_search_text


ensure_db()
st.title("Collection par personne")

with get_session() as session:
    people = get_people(session)
    categories = sorted({s.category_code for s in get_stickers(session) if s.category_code})
    if not people:
        render_empty_import_hint()
        st.stop()

person = st.selectbox("Personne", people, format_func=lambda p: p.name)
c1, c2 = st.columns([1, 1])
status = c1.segmented_control("Filtre", ["Tous", "Manquants", "Possédés", "Doubles", "À compléter"], default="Tous")
category = c2.selectbox("Catégorie / pays", ["Toutes"] + categories)
query = st.text_input("Recherche", placeholder="Code, joueur, équipe...")
category_filter = None if category == "Toutes" else category

with get_session() as session:
    stats = get_person_stats(session, person.id)
    base_status = "Manquants" if status == "À compléter" else status
    rows = get_collection_rows(session, person.id, base_status, category_filter)
    people_for_help = [p for p in get_people(session) if p.id != person.id]
    exchange_help = {}
    sale_help = {}
    if status == "À compléter":
        for other in people_for_help:
            for item in get_tradeable_stickers_between(session, other.id, person.id):
                exchange_help[item["sticker_id"]] = exchange_help.get(item["sticker_id"], 0) + 1
            for item in get_sale_candidates(session, seller_id=other.id, buyer_id=person.id):
                sale_help[item["sticker_id"]] = sale_help.get(item["sticker_id"], 0) + 1

if query:
    needle = normalize_search_text(query)
    rows = [
        row
        for row in rows
        if needle
        in normalize_search_text(
            " ".join(
                [
                    row["display_code"] or "",
                    row["sticker_code"] or "",
                    row["player_name"] or "",
                    row["label"] or "",
                    row["team_name"] or "",
                    row["category_name"] or "",
                    row["category_code"] or "",
                ]
            )
        )
    ]

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Possédés", stats["owned_distinct"])
c2.metric("Exemplaires", stats["total_copies"])
c3.metric("Doubles", stats["duplicates"])
c4.metric("Manquants", stats["missing"])
c5.metric("Complétion", f"{stats['completion']:.1f}%")

display_rows = []
for row in rows:
    display = {
        "Code": row["display_code"],
        "Sticker": row["player_name"] or row["label"] or row["display_code"],
        "Équipe / catégorie": row["team_name"] or row["category_name"] or row["category_code"],
        "Quantité": row["quantity"],
        "Doubles": row["duplicate_count"],
    }
    if status == "À compléter":
        display["Échanges"] = exchange_help.get(row["sticker_id"], 0)
        display["Ventes"] = sale_help.get(row["sticker_id"], 0)
    display_rows.append(display)

data = pd.DataFrame(display_rows)
if data.empty:
    st.caption("Aucun sticker dans ce filtre.")
else:
    st.dataframe(
        data,
        use_container_width=True,
        hide_index=True,
        height=560,
        column_config={
            "Code": st.column_config.TextColumn("Code", width="small"),
            "Sticker": st.column_config.TextColumn("Sticker", width="large"),
            "Équipe / catégorie": st.column_config.TextColumn("Équipe / catégorie", width="medium"),
            "Quantité": st.column_config.NumberColumn("Quantité", width="small"),
            "Doubles": st.column_config.NumberColumn("Doubles", width="small"),
            "Échanges": st.column_config.NumberColumn("Échanges", width="small", help="Personnes qui peuvent l'échanger"),
            "Ventes": st.column_config.NumberColumn("Ventes", width="small", help="Personnes qui peuvent le vendre"),
        },
    )
