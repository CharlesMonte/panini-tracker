from __future__ import annotations

import pandas as pd
import streamlit as st

from src.db import get_session
from src.repositories import get_people
from src.services.undo_service import get_recent_actions, human_action_label, undo_action
from src.ui.components import ensure_db
from src.utils.normalization import normalize_search_text


ensure_db()
st.title("Historique")
st.caption("Suivi des dernières actions, avec annulation quand l'action est simple et sûre.")

with get_session() as session:
    people = get_people(session)
    actions = get_recent_actions(session, limit=200)

c1, c2, c3 = st.columns(3)
person = c1.selectbox("Personne", ["Toutes"] + [p.name for p in people])
action_types = ["Tous"] + sorted({action["action"] for action in actions}, key=human_action_label)
action_type = c2.selectbox("Action", action_types, format_func=lambda value: "Tous" if value == "Tous" else human_action_label(value))
search = c3.text_input("Recherche")

filtered = actions
if person != "Toutes":
    filtered = [action for action in filtered if action["personne"] == person]
if action_type != "Tous":
    filtered = [action for action in filtered if action["action"] == action_type]
if search:
    needle = normalize_search_text(search)
    filtered = [
        action
        for action in filtered
            if needle
        in normalize_search_text(
            " ".join(
                str(value or "")
                for value in [action["personne"], action["sticker"], action["nom"], action["action_label"]]
            )
        )
    ]

display = pd.DataFrame(
    [
        {
            "Date": action["date"],
            "Action": action["action_label"],
            "Personne": action["personne"],
            "Sticker": action["sticker"],
            "Nom": action["nom"],
            "Quantité": f"{action['avant']} → {action['après']}",
            "Annulable": "Oui" if action["annulable"] else "Non",
        }
        for action in filtered
    ]
)

if display.empty:
    st.caption("Aucune action trouvée.")
else:
    st.dataframe(display, use_container_width=True, hide_index=True, height=420)

st.subheader("Annulation")
undoable = [action for action in filtered if action["annulable"]]
if not undoable:
    st.caption("Aucune action annulable dans le filtre courant.")
else:
    selected = st.selectbox(
        "Action à annuler",
        undoable,
        format_func=lambda action: f"{action['action_label']} · {action['personne']} · {action['sticker']} · {action['avant']} → {action['après']}",
    )
    actor_name = st.text_input("Annulé par", placeholder="Optionnel")
    if st.button("Annuler cette action", type="primary"):
        try:
            with get_session() as session:
                undo_action(session, selected["id"], actor_name)
            st.success("Action annulée.")
            st.rerun()
        except ValueError as exc:
            st.error(str(exc))
