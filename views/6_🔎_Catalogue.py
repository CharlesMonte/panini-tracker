from __future__ import annotations

import pandas as pd
import streamlit as st
from sqlalchemy import select

from src.db import get_session
from src.models import Holding
from src.repositories import get_people, get_stickers
from src.services.collection_service import filter_stickers_by_kind, get_sticker_kind, search_stickers
from src.ui.components import ensure_db, render_empty_import_hint
from src.ui.patterns import render_sticker_card


ensure_db()
st.title("Catalogue")
st.caption("Vue simple de l'album: retrouver un sticker, voir son type et savoir rapidement s'il circule dans le groupe.")

c1, c2, c3, c4 = st.columns([2, 1, 1, 1])
query = c1.text_input("Recherche", placeholder="Code, joueur, équipe, label...")
kind_filter = c3.selectbox("Type", ["Tous", "Joueur", "Logo", "Photo équipe", "Foil"])
view_mode = c4.segmented_control("Vue", ["Table", "Cartes"], default="Table")

with get_session() as session:
    people = get_people(session)
    stickers = get_stickers(session)
    if not stickers:
        render_empty_import_hint()
        st.stop()
    categories = sorted({s.category_code for s in stickers if s.category_code})
    category = c2.selectbox("Catégorie / pays", ["Toutes"] + categories)
    rows = search_stickers(session, query, None if category == "Toutes" else category)
    quantities = {(h.person_id, h.sticker_id): h.quantity for h in session.scalars(select(Holding))}

for row in rows:
    owners = [p.name for p in people if quantities.get((p.id, row["sticker_id"]), 0) > 0]
    seekers = [p.name for p in people if quantities.get((p.id, row["sticker_id"]), 0) == 0]
    doubles = [p.name for p in people if quantities.get((p.id, row["sticker_id"]), 0) > 1]
    row["owners"] = owners
    row["seekers"] = seekers
    row["doubles"] = doubles
    row["kind"] = get_sticker_kind(row)

rows = filter_stickers_by_kind(rows, kind_filter)

m1, m2, m3, m4 = st.columns(4)
m1.metric("Stickers affichés", len(rows))
m2.metric("Dans l'album", len(stickers))
m3.metric("Collectionneurs", len(people))
m4.metric("Avec doubles", sum(1 for row in rows if row["doubles"]))

display_rows = [
    {
        "Code": row["display_code"],
        "Sticker": row["player_name"] or row["label"] or row["display_code"],
        "Équipe / catégorie": row["team_name"] or row["category_name"] or row["category_code"],
        "Type": row["kind"],
        "Possédé par": len(row["owners"]),
        "En double chez": len(row["doubles"]),
        "Recherché par": len(row["seekers"]),
    }
    for row in rows
]

data = pd.DataFrame(display_rows)
if data.empty:
    st.caption("Aucun sticker trouvé.")
    st.stop()

if view_mode == "Table":
    st.dataframe(
        data,
        use_container_width=True,
        hide_index=True,
        height=520,
        column_config={
            "Code": st.column_config.TextColumn("Code", width="small"),
            "Sticker": st.column_config.TextColumn("Sticker", width="large"),
            "Équipe / catégorie": st.column_config.TextColumn("Équipe / catégorie", width="medium"),
            "Type": st.column_config.TextColumn("Type", width="small"),
            "Possédé par": st.column_config.NumberColumn("Possédé par", width="small"),
            "En double chez": st.column_config.NumberColumn("En double chez", width="small"),
            "Recherché par": st.column_config.NumberColumn("Recherché par", width="small"),
        },
    )
else:
    st.caption("Affichage limité aux 24 premiers résultats du filtre.")
    for start in range(0, min(len(rows), 24), 3):
        cols = st.columns(3)
        for col, row in zip(cols, rows[start : start + 3]):
            with col:
                render_sticker_card(row)
                st.caption(
                    f"{len(row['owners'])} possèdent · {len(row['doubles'])} doubles · {len(row['seekers'])} cherchent"
                )

st.subheader("Détail d'un sticker")
selected = st.selectbox(
    "Sticker",
    rows,
    format_func=lambda row: f"{row['display_code']} - {row['player_name'] or row['label'] or row['team_name'] or ''}",
)

d1, d2, d3 = st.columns(3)
d1.metric("Possédé par", len(selected["owners"]))
d2.metric("En double chez", len(selected["doubles"]))
d3.metric("Recherché par", len(selected["seekers"]))

st.markdown(
    f"""
    <div class="panini-card">
      <div style="font-size: 0.85rem; opacity: 0.75;">{selected["display_code"]} · {selected["kind"]}</div>
      <div style="font-size: 1.25rem; font-weight: 700; margin-top: 0.15rem;">{selected["player_name"] or selected["label"] or selected["display_code"]}</div>
      <div style="opacity: 0.8; margin-top: 0.1rem;">{selected["team_name"] or selected["category_name"] or selected["category_code"] or ""}</div>
    </div>
    """,
    unsafe_allow_html=True,
)

detail_cols = st.columns(3)
detail_cols[0].write("Possèdent")
detail_cols[0].caption(", ".join(selected["owners"]) or "Personne")
detail_cols[1].write("Ont en double")
detail_cols[1].caption(", ".join(selected["doubles"]) or "Personne")
detail_cols[2].write("Cherchent")
detail_cols[2].caption(", ".join(selected["seekers"]) or "Personne")

st.subheader("Actions")
a1, a2, a3 = st.columns(3)
a1.page_link("views/2_📦_Ajouter_des_stickers.py", label="Ajouter à une personne", icon="📦")
a2.page_link("views/4_🔁_Echanges.py", label="Voir échanges", icon="🔁")
a3.page_link("views/5_💶_Achats_Ventes.py", label="Voir ventes", icon="💶")
