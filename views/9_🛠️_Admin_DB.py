from __future__ import annotations

import pandas as pd
import streamlit as st

from src.db import get_session
from src.repositories import get_people
from src.services.admin_service import (
    create_person,
    delete_person,
    delete_sticker,
    ensure_full_holdings_matrix,
    get_action_type_rows,
    get_category_admin_rows,
    get_database_overview,
    get_import_admin_rows,
    get_people_admin_rows,
    get_sticker_admin_rows,
    purge_action_log,
    purge_import_runs,
    set_person_active,
    update_person_display_order,
    update_sticker_metadata,
)
from src.ui.components import ensure_db, show_table


ensure_db()
st.title("Administration DB")
st.caption(
    "Zone avancée pour corriger la base locale. Les actions destructives sont repliées et demandent une confirmation explicite."
)

actor_name = st.text_input("Qui fait l'action ?", placeholder="Optionnel")

tab_people, tab_overview, tab_stickers, tab_maintenance, tab_history = st.tabs(
    ["Personnes", "Vue DB", "Stickers", "Maintenance", "Imports / Historique"]
)


def _human_people_rows(rows: list[dict]) -> pd.DataFrame:
    return pd.DataFrame(rows).rename(
        columns={
            "id": "ID",
            "name": "Nom",
            "display_order": "Ordre",
            "active": "Actif",
            "holdings": "Lignes collection",
            "total_quantity": "Exemplaires",
            "trades": "Échanges",
            "trade_lines": "Lignes échange",
        }
    )


def _human_sticker_rows(rows: list[dict]) -> pd.DataFrame:
    return pd.DataFrame(rows).rename(
        columns={
            "id": "ID",
            "album_order": "Ordre album",
            "sticker_code": "Code normalisé",
            "display_code": "Code",
            "category_code": "Catégorie",
            "category_name": "Nom catégorie",
            "player_name": "Joueur",
            "team_name": "Équipe",
            "label": "Libellé",
            "is_foil": "Foil",
            "is_team_photo": "Photo équipe",
            "is_emblem": "Logo",
            "holdings": "Lignes collection",
            "total_quantity": "Exemplaires",
        }
    )

with tab_overview:
    with get_session() as session:
        overview = get_database_overview(session)
        categories = get_category_admin_rows(session)
        action_types = get_action_type_rows(session)

    st.subheader("Santé de la base")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Personnes", overview["people_total"], f"{overview['people_active']} actives")
    c2.metric("Stickers", overview["stickers_total"])
    c3.metric("Exemplaires", overview["total_copies"])
    c4.metric("Lignes collection manquantes", overview["holdings_missing_rows"])

    c5, c6, c7, c8 = st.columns(4)
    c5.metric("Lignes collection", overview["holdings_total"])
    c6.metric("Lignes non zéro", overview["holdings_nonzero"])
    c7.metric("Échanges", overview["trades"])
    c8.metric("Actions loggées", overview["actions"])

    with st.expander("Catégories", expanded=False):
        show_table(pd.DataFrame(categories), height=320)

    with st.expander("Actions par type", expanded=False):
        show_table(pd.DataFrame(action_types), height=260)

with tab_people:
    with get_session() as session:
        people_rows = get_people_admin_rows(session)
        people = get_people(session, active_only=False)

    left, right = st.columns([1.2, 1])
    with left:
        st.subheader("Personnes en base")
        show_table(_human_people_rows(people_rows), height=420)

    with right:
        st.subheader("Ajouter / réactiver")
        name = st.text_input("Nom", key="create_person_name")
        display_order = st.number_input("Ordre", min_value=0, step=1, value=0, key="create_person_order")
        if st.button("Créer / réactiver", type="primary"):
            try:
                with get_session() as session:
                    person = create_person(session, name, int(display_order) if display_order else None, actor_name)
                st.success(f"{person.name} est disponible.")
                st.rerun()
            except ValueError as exc:
                st.error(str(exc))

    st.divider()
    if not people:
        st.info("Aucune personne en base.")
    else:
        selected = st.selectbox(
            "Personne à gérer",
            people,
            format_func=lambda p: f"{p.name} ({'active' if p.active else 'inactive'})",
        )
        selected_row = next((row for row in people_rows if row["id"] == selected.id), None)
        if selected_row:
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Lignes collection", selected_row["holdings"])
            c2.metric("Quantité totale", selected_row["total_quantity"])
            c3.metric("Échanges", selected_row["trades"])
            c4.metric("Lignes échange", selected_row["trade_lines"])

        st.subheader("Statut et ordre")
        c1, c2, c3 = st.columns([1, 1, 2])
        if selected.active:
            if c1.button("Désactiver"):
                with get_session() as session:
                    set_person_active(session, selected.id, False, actor_name)
                st.success(f"{selected.name} est désactivé.")
                st.rerun()
        else:
            if c1.button("Réactiver", type="primary"):
                with get_session() as session:
                    set_person_active(session, selected.id, True, actor_name)
                st.success(f"{selected.name} est réactivé.")
                st.rerun()

        new_order = c2.number_input("Ordre d'affichage", min_value=0, step=1, value=int(selected.display_order))
        if c3.button("Mettre à jour l'ordre"):
            with get_session() as session:
                update_person_display_order(session, selected.id, int(new_order), actor_name)
            st.success("Ordre mis à jour.")
            st.rerun()

        with st.expander("Suppression définitive", expanded=False):
            st.warning("Supprime la personne et ses quantités. Les échanges liés peuvent être supprimés par cascade DB.")
            confirm_name = st.text_input(f"Tapez exactement le nom pour confirmer: {selected.name}")
            confirm_delete = st.checkbox("Je confirme la suppression définitive de cette personne.")
            if st.button("Supprimer définitivement", disabled=not confirm_delete):
                try:
                    with get_session() as session:
                        deleted_name = delete_person(session, selected.id, confirm_name, actor_name)
                    st.success(f"{deleted_name} a été supprimé définitivement.")
                    st.rerun()
                except ValueError as exc:
                    st.error(str(exc))

with tab_stickers:
    st.subheader("Recherche et édition stickers")
    with get_session() as session:
        categories = [row["category_code"] for row in get_category_admin_rows(session) if row["category_code"]]

    c1, c2, c3 = st.columns([2, 1, 1])
    query = c1.text_input("Recherche", placeholder="MEX12, joueur, équipe, label...")
    category = c2.selectbox("Catégorie", ["Toutes"] + categories)
    limit = c3.number_input("Limite", min_value=50, max_value=5000, value=1000, step=50)

    with get_session() as session:
        sticker_rows = get_sticker_admin_rows(
            session,
            query=query,
            category=None if category == "Toutes" else category,
            limit=int(limit),
        )
    show_table(_human_sticker_rows(sticker_rows), height=380)

    if sticker_rows:
        selected_row = st.selectbox(
            "Sticker à modifier",
            sticker_rows,
            format_func=lambda row: f"{row['display_code']} - {row['player_name'] or row['label'] or row['team_name'] or ''}",
        )
        with st.form("edit_sticker_form"):
            c1, c2, c3 = st.columns(3)
            sticker_code = c1.text_input("Code", value=selected_row["sticker_code"])
            album_order = c2.number_input("Ordre album", min_value=0, step=1, value=int(selected_row["album_order"]))
            category_code = c3.text_input("Code catégorie", value=selected_row["category_code"] or "")
            category_name = st.text_input("Nom catégorie", value=selected_row["category_name"] or "")
            player_name = st.text_input("Joueur", value=selected_row["player_name"] or "")
            team_name = st.text_input("Équipe", value=selected_row["team_name"] or "")
            label = st.text_area("Libellé", value=selected_row["label"] or "", height=90)
            f1, f2, f3 = st.columns(3)
            is_foil = f1.checkbox("Foil", value=bool(selected_row["is_foil"]))
            is_team_photo = f2.checkbox("Photo équipe", value=bool(selected_row["is_team_photo"]))
            is_emblem = f3.checkbox("Logo", value=bool(selected_row["is_emblem"]))
            submitted = st.form_submit_button("Enregistrer", type="primary")
        if submitted:
            try:
                with get_session() as session:
                    update_sticker_metadata(
                        session,
                        selected_row["id"],
                        sticker_code=sticker_code,
                        album_order=int(album_order),
                        category_code=category_code or None,
                        category_name=category_name or None,
                        player_name=player_name or None,
                        team_name=team_name or None,
                        label=label or None,
                        is_foil=is_foil,
                        is_team_photo=is_team_photo,
                        is_emblem=is_emblem,
                        actor_name=actor_name,
                    )
                st.success("Sticker mis à jour.")
                st.rerun()
            except ValueError as exc:
                st.error(str(exc))

        with st.expander("Suppression sticker", expanded=False):
            st.warning("Supprime le sticker, ses lignes collection et les lignes d'échange associées.")
            confirm_code = st.text_input(f"Tapez exactement le code pour confirmer: {selected_row['sticker_code']}")
            confirm_sticker_delete = st.checkbox("Je confirme la suppression définitive de ce sticker.")
            if st.button("Supprimer ce sticker", disabled=not confirm_sticker_delete):
                try:
                    with get_session() as session:
                        deleted_code = delete_sticker(session, selected_row["id"], confirm_code, actor_name)
                    st.success(f"{deleted_code} a été supprimé.")
                    st.rerun()
                except ValueError as exc:
                    st.error(str(exc))

with tab_maintenance:
    with st.expander("Réparer les lignes collection", expanded=False):
        st.caption("Crée les lignes collection manquantes à quantité 0 pour chaque personne/sticker.")
        include_inactive = st.checkbox("Inclure les personnes inactives", value=True)
        if st.button("Créer les lignes manquantes", type="primary"):
            with get_session() as session:
                result = ensure_full_holdings_matrix(session, include_inactive=include_inactive, actor_name=actor_name)
            st.success("Maintenance terminée.")
            st.write(result)

    with st.expander("Purge imports", expanded=False):
        st.caption("Supprime uniquement les lignes de suivi dans la table imports, pas les données importées.")
        confirm_imports = st.text_input('Confirmation imports: tapez "PURGE IMPORTS"')
        if st.button("Purger imports"):
            try:
                with get_session() as session:
                    count = purge_import_runs(session, confirm_imports, actor_name)
                st.success(f"{count} import(s) supprimé(s).")
                st.rerun()
            except ValueError as exc:
                st.error(str(exc))

    with st.expander("Purge historique", expanded=False):
        st.warning("Supprime tout l'historique action_log. Cette opération n'est pas traçable dans action_log par définition.")
        confirm_history = st.text_input('Confirmation historique: tapez "PURGE HISTORY"')
        if st.button("Purger historique"):
            try:
                with get_session() as session:
                    count = purge_action_log(session, confirm_history)
                st.success(f"{count} action(s) supprimée(s).")
                st.rerun()
            except ValueError as exc:
                st.error(str(exc))

with tab_history:
    with get_session() as session:
        imports = get_import_admin_rows(session, limit=200)
        action_types = get_action_type_rows(session)

    st.subheader("Imports récents")
    show_table(pd.DataFrame(imports), height=420)

    st.subheader("Actions par type")
    show_table(pd.DataFrame(action_types), height=260)
