from __future__ import annotations

import streamlit as st
import pandas as pd
from sqlalchemy import select

from src.db import get_session
from src.models import Holding
from src.repositories import get_people
from src.services.batch_service import apply_batch_add, preview_batch_add
from src.services.collection_service import add_quantity, search_stickers, set_quantity
from src.services.undo_service import get_recent_actions, undo_action, undo_batch
from src.ui.components import ensure_db, render_empty_import_hint
from src.ui.patterns import render_sticker_card, sticker_option_label


ensure_db()
st.title("Saisie rapide")
st.caption("Pensé pour saisir rapidement les cartes après ouverture de pochettes.")

with get_session() as session:
    people = get_people(session)
    if not people:
        render_empty_import_hint()
        st.stop()

person = st.selectbox("Pour qui ?", people, format_func=lambda p: p.name)
actor_name = st.text_input("Qui fait l'action ?", placeholder="Optionnel")

tab_batch, tab_one = st.tabs(["Coller une liste", "Chercher un sticker"])

with tab_batch:
    raw_codes = st.text_area(
        "Codes à ajouter pendant cette session",
        placeholder="MEX1\nMEX2\nBRA14\nFWC3",
        height=220,
        help="Un code par ligne. Les doublons sont conservés: si MEX1 apparaît deux fois, +2 sera ajouté.",
    )

    p1, p2 = st.columns([1, 1])
    if p1.button("Prévisualiser la session", type="primary"):
        with get_session() as session:
            preview = preview_batch_add(session, person.id, raw_codes)
        st.session_state.quick_batch_preview = {
            "person_id": person.id,
            "person_name": person.name,
            "raw_codes": raw_codes,
            "preview": preview,
        }
        st.session_state.pop("last_quick_batch", None)

    stored_preview = st.session_state.get("quick_batch_preview")
    if stored_preview and stored_preview["person_id"] != person.id:
        st.info("La prévisualisation affichée concerne une autre personne. Relance une prévisualisation.")
        stored_preview = None

    if stored_preview:
        preview = stored_preview["preview"]
        c1, c2, c3 = st.columns(3)
        c1.metric("Ajouts valides", preview["valid_count"])
        c2.metric("Codes inconnus", preview["unknown_count"])
        c3.metric("Doublons saisis", len(preview["duplicate_codes"]))

        valid_rows = [
            {
                "Code": item["display_code"],
                "Sticker": item.get("player_name") or item.get("label") or item["display_code"],
                "Équipe / catégorie": item.get("team_name") or item.get("category_name") or item.get("category_code"),
                "Quantité actuelle": item["current_quantity"],
                "Ajout": item["count_to_add"],
                "Après": item["new_quantity"],
            }
            for item in preview["valid_items"]
        ]
        if valid_rows:
            st.dataframe(pd.DataFrame(valid_rows), use_container_width=True, hide_index=True, height=300)
        else:
            st.caption("Aucun code valide dans cette session.")

        if preview["unknown_items"]:
            st.error("Codes introuvables: " + ", ".join(item["code"] for item in preview["unknown_items"]))
        if preview["duplicate_codes"]:
            st.warning("Codes présents plusieurs fois dans la saisie: " + ", ".join(preview["duplicate_codes"]))

        if p2.button("Appliquer la session", disabled=not preview["valid_items"]):
            try:
                with get_session() as session:
                    result = apply_batch_add(session, person.id, preview["items"], actor_name)
                st.session_state.last_quick_batch = result
                st.success(
                    f"{result['added_count']} sticker(s) ajouté(s) sur "
                    f"{result['updated_stickers']} code(s) pour {person.name}."
                )
                st.rerun()
            except ValueError as exc:
                st.error(str(exc))

    last_batch = st.session_state.get("last_quick_batch")
    if last_batch:
        st.success(
            f"Dernière session appliquée: {last_batch['added_count']} ajout(s) "
            f"sur {last_batch['updated_stickers']} sticker(s)."
        )
        if st.button("Annuler cette session"):
            try:
                with get_session() as session:
                    undo_batch(session, last_batch["batch_id"], actor_name)
                st.session_state.pop("last_quick_batch", None)
                st.success("Session annulée.")
                st.rerun()
            except ValueError as exc:
                st.error(str(exc))

with tab_one:
    query = st.text_input("Rechercher", placeholder="MEX12, Mbappé, France...")
    with get_session() as session:
        results = search_stickers(session, query)[:100] if query else []
    if results:
        selected = st.selectbox("Sticker", results, format_func=sticker_option_label)
        with get_session() as session:
            current_qty = session.scalar(
                select(Holding.quantity).where(
                    Holding.person_id == person.id,
                    Holding.sticker_id == selected["sticker_id"],
                )
            ) or 0
        render_sticker_card(selected)
        m1, m2 = st.columns(2)
        m1.metric("Quantité actuelle", current_qty)
        m2.metric("Doubles", max(current_qty - 1, 0))
        c1, c2, c3 = st.columns(3)
        if c1.button("+1", type="primary"):
            with get_session() as session:
                add_quantity(session, person.id, selected["sticker_id"], 1, actor_name)
            st.success("Sticker ajouté.")
            st.rerun()
        if c2.button("-1"):
            try:
                with get_session() as session:
                    add_quantity(session, person.id, selected["sticker_id"], -1, actor_name)
                st.success("Sticker retiré.")
                st.rerun()
            except ValueError as exc:
                st.error(str(exc))
        exact = c3.number_input("Quantité", min_value=0, step=1, value=int(current_qty))
        if st.button("Définir quantité exacte"):
            with get_session() as session:
                set_quantity(session, person.id, selected["sticker_id"], int(exact), actor_name)
            st.success("Quantité mise à jour.")
            st.rerun()
    elif query:
        st.warning("Aucun sticker trouvé.")

st.subheader("Dernières actions")
with get_session() as session:
    actions = get_recent_actions(session, limit=8)

if not actions:
    st.caption("Aucune action récente.")
else:
    for action in actions:
        cols = st.columns([1.1, 1.2, 1.8, 0.8, 0.9])
        cols[0].write(action["action_label"])
        cols[1].write(action["personne"] or "")
        cols[2].write(f"{action['sticker'] or ''} · {action['nom'] or ''}")
        cols[3].write(f"{action['avant']} → {action['après']}")
        if action["annulable"]:
            if cols[4].button("Annuler", key=f"undo_{action['id']}"):
                try:
                    with get_session() as session:
                        undo_action(session, action["id"], actor_name)
                    st.success("Action annulée.")
                    st.rerun()
                except ValueError as exc:
                    st.error(str(exc))
        else:
            cols[4].caption("Non annulable")
