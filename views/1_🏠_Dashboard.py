from __future__ import annotations

import pandas as pd
import streamlit as st

from src.db import get_session
from src.repositories import get_people, get_stickers
from src.services.collection_service import get_all_people_stats, get_duplicates, get_missing, get_person_stats
from src.services.exchange_service import get_opportunity_summaries
from src.ui.components import render_empty_import_hint


st.title("Panini Tracker 2026")
st.caption("Collection partagée, doubles, manquants et échanges équivalents.")

with get_session() as session:
    people = get_people(session)
    stickers = get_stickers(session)
    if not people or not stickers:
        render_empty_import_hint()
        st.page_link("views/8_⚙️_Import_Export.py", label="Importer un Excel", icon="⚙️")
        st.stop()

    stats = get_all_people_stats(session)
    exchange_summaries, sale_summaries = get_opportunity_summaries(session, limit=4)

cols = st.columns(4)
cols[0].metric("Stickers album", len(stickers))
cols[1].metric("Collectionneurs", len(people))
cols[2].metric("Échanges réalisables", sum(row["count"] for row in exchange_summaries))
cols[3].metric("Ventes à regarder", sum(row["count"] for row in sale_summaries))

st.subheader("Actions rapides")
a1, a2, a3, a4 = st.columns(4)
a1.page_link("views/2_📦_Ajouter_des_stickers.py", label="Ajouter des stickers", icon="📦")
a2.page_link("views/4_🔁_Echanges.py", label="Préparer un échange", icon="🔁")
a3.page_link("views/3_👤_Collection.py", label="Voir mes manquants", icon="👤")
a4.page_link("views/5_💶_Achats_Ventes.py", label="Voir les ventes", icon="💶")

st.subheader("Personne à suivre")
tracked = st.selectbox("Choisir une personne", people, format_func=lambda p: p.name, label_visibility="collapsed")
with get_session() as session:
    tracked_stats = get_person_stats(session, tracked.id)
    tracked_missing = get_missing(session, tracked.id)[:5]
    tracked_duplicates = get_duplicates(session, tracked.id)[:5]

todo, trade_block, sale_block = st.columns(3)
with todo:
    st.markdown("**À faire**")
    st.metric("Manquants", tracked_stats["missing"])
    st.caption("Premiers manquants: " + ", ".join(row["display_code"] for row in tracked_missing) if tracked_missing else "Album complet.")
with trade_block:
    st.markdown("**Échanges intéressants**")
    helpful = [
        row
        for row in exchange_summaries
        if row["person_a_id"] == tracked.id or row["person_b_id"] == tracked.id
    ]
    if helpful:
        for row in helpful[:2]:
            st.caption(
                f"{row['person_a']} ↔ {row['person_b']}: jusqu'à {row['count']} échange(s)"
            )
    else:
        st.caption("Aucun binôme prioritaire dans le résumé rapide.")
    st.page_link("views/4_🔁_Echanges.py", label="Préparer", icon="🔁")
with sale_block:
    st.markdown("**Ventes possibles**")
    relevant_sales = [row for row in sale_summaries if row["to_id"] == tracked.id or row["from_id"] == tracked.id]
    if relevant_sales:
        for row in relevant_sales[:2]:
            st.caption(f"{row['from']} → {row['to']}: {row['count']} carte(s)")
    else:
        st.caption("Aucune vente prioritaire dans le résumé rapide.")
    st.page_link("views/5_💶_Achats_Ventes.py", label="Ouvrir", icon="💶")

st.subheader("Progression par personne")
progress_df = pd.DataFrame(stats)
progress_df["completion"] = progress_df["completion"].map(lambda value: f"{value:.1f}%")
progress_df["duplicate_rate"] = progress_df["duplicate_rate"].map(lambda value: f"{value:.1f}%")
st.dataframe(
    progress_df[
        ["person_name", "owned_distinct", "total_copies", "duplicates", "duplicate_rate", "missing", "completion"]
    ].rename(
        columns={
            "person_name": "Personne",
            "owned_distinct": "Possédés",
            "total_copies": "Exemplaires",
            "duplicates": "Doubles",
            "duplicate_rate": "% doubles",
            "missing": "Manquants",
            "completion": "% complétion",
        }
    ),
    use_container_width=True,
    hide_index=True,
)

left, right = st.columns(2)
with left:
    st.subheader("Échanges à regarder")
    if not exchange_summaries:
        st.caption("Aucun échange équivalent disponible.")
    for row in exchange_summaries:
        st.markdown(
            f"""
            <div class="panini-card" style="margin-bottom: 0.6rem;">
              <div style="font-weight: 700;">{row["person_a"]} ↔ {row["person_b"]}</div>
              <div style="opacity: 0.8;">Jusqu'à {row["count"]} échange(s) 1 contre 1 réalisable(s)</div>
              <div style="opacity: 0.65; font-size: 0.9rem; margin-top: 0.25rem;">
                {row["person_a"]} peut donner {row["a_can_give"]} carte(s), {row["person_b"]} peut donner {row["b_can_give"]} carte(s)
              </div>
              <div style="opacity: 0.55; font-size: 0.85rem; margin-top: 0.15rem;">
                {row["choice_count"]} combinaison(s) de choix possibles
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.link_button("Préparer ce binôme", f"Echanges?person_a_id={row['person_a_id']}&person_b_id={row['person_b_id']}")
    st.page_link("views/4_🔁_Echanges.py", label="Ouvrir les échanges", icon="🔁")
with right:
    st.subheader("Ventes à regarder")
    if not sale_summaries:
        st.caption("Aucune vente disponible.")
    for row in sale_summaries:
        st.markdown(
            f"""
            <div class="panini-card" style="margin-bottom: 0.6rem;">
              <div style="font-weight: 700;">{row["from"]} peut vendre à {row["to"]}</div>
              <div style="opacity: 0.8;">{row["count"]} sticker(s) potentiels</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.link_button("Ouvrir ce binôme", f"Achats-Ventes?seller_id={row['from_id']}&buyer_id={row['to_id']}")
    st.page_link("views/5_💶_Achats_Ventes.py", label="Ouvrir les achats / ventes", icon="💶")
