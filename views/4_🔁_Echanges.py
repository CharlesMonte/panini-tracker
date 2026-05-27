from __future__ import annotations

import pandas as pd
import streamlit as st

from src.db import get_session
from src.repositories import get_people
from src.services.exchange_service import (
    apply_batch_equivalent_trades,
    apply_equivalent_trade,
    get_tradeable_stickers_between,
    preview_batch_equivalent_trades,
)
from src.ui.components import ensure_db, render_empty_import_hint
from src.ui.patterns import render_sticker_card, sticker_option_label
from src.utils.normalization import normalize_search_text


ensure_db()
st.title("Échanges équivalents")

with get_session() as session:
    people = get_people(session)
    if len(people) < 2:
        render_empty_import_hint()
        st.stop()

def _query_int(name: str) -> int | None:
    value = st.query_params.get(name)
    if isinstance(value, list):
        value = value[0] if value else None
    try:
        return int(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def _filter_rows(rows: list[dict], query: str) -> list[dict]:
    needle = normalize_search_text(query)
    if not needle:
        return rows
    return [
        row
        for row in rows
        if needle
        in normalize_search_text(
            " ".join(
                [
                    row["display_code"] or "",
                    row["sticker_code"] or "",
                    row["label"] or "",
                    row.get("team_name") or "",
                    row.get("category_name") or "",
                    row.get("category_code") or "",
                ]
            )
        )
    ]


def _display_rows(rows: list[dict]) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "Code": row["display_code"],
                "Sticker": row["label"],
                "Équipe / catégorie": row.get("team_name") or row.get("category_name") or row.get("category_code"),
                "Quantité donneur": row["giver_quantity"],
            }
            for row in rows
        ]
    )


def _show_tradeable_table(rows: list[dict]) -> None:
    data = _display_rows(rows)
    if data.empty:
        st.caption("Aucun sticker disponible.")
        return
    st.dataframe(
        data,
        use_container_width=True,
        hide_index=True,
        height=360,
        column_config={
            "Code": st.column_config.TextColumn("Code", width="small"),
            "Sticker": st.column_config.TextColumn("Sticker", width="large"),
            "Équipe / catégorie": st.column_config.TextColumn("Équipe / catégorie", width="medium"),
            "Quantité donneur": st.column_config.NumberColumn("Quantité donneur", width="small"),
        },
    )


if "exchange_a_id" not in st.session_state:
    st.session_state.exchange_a_id = people[0].id
if "exchange_b_id" not in st.session_state:
    st.session_state.exchange_b_id = people[1].id if len(people) > 1 else people[0].id

people_ids = {person.id for person in people}
qp_pair = (_query_int("person_a_id"), _query_int("person_b_id"))
if (
    qp_pair[0] in people_ids
    and qp_pair[1] in people_ids
    and qp_pair[0] != qp_pair[1]
    and st.session_state.get("exchange_prefill_pair") != qp_pair
):
    st.session_state.exchange_a_id, st.session_state.exchange_b_id = qp_pair
    st.session_state.exchange_prefill_pair = qp_pair

def _index_for(person_id: int) -> int:
    return next((idx for idx, person in enumerate(people) if person.id == person_id), 0)


c1, c2, c3 = st.columns([1, 1, 0.35])
person_a = c1.selectbox("Personne 1", people, index=_index_for(st.session_state.exchange_a_id), format_func=lambda p: p.name)
person_b = c2.selectbox("Personne 2", people, index=_index_for(st.session_state.exchange_b_id), format_func=lambda p: p.name)
st.session_state.exchange_a_id = person_a.id
st.session_state.exchange_b_id = person_b.id
if c3.button("Inverser"):
    st.session_state.exchange_a_id, st.session_state.exchange_b_id = person_b.id, person_a.id
    st.rerun()

if st.session_state.get("last_exchange_summary"):
    st.success(st.session_state.pop("last_exchange_summary"))

if person_a.id == person_b.id:
    st.warning("Choisis deux personnes différentes pour préparer un échange.")
    st.stop()

search = st.text_input("Filtrer les stickers", placeholder="Code, joueur, équipe, catégorie...")

with get_session() as session:
    a_to_b_all = get_tradeable_stickers_between(session, person_a.id, person_b.id)
    b_to_a_all = get_tradeable_stickers_between(session, person_b.id, person_a.id)

a_to_b = _filter_rows(a_to_b_all, search)
b_to_a = _filter_rows(b_to_a_all, search)

m1, m2, m3 = st.columns(3)
m1.metric(f"{person_a.name} peut donner", len(a_to_b_all))
m2.metric(f"{person_b.name} peut donner", len(b_to_a_all))
m3.metric("Échanges réalisables", min(len(a_to_b_all), len(b_to_a_all)))
st.caption(
    f"{len(a_to_b_all) * len(b_to_a_all)} combinaison(s) de choix possibles, "
    f"mais au maximum {min(len(a_to_b_all), len(b_to_a_all))} échange(s) 1 contre 1 réalisable(s)."
)

left, right = st.columns(2)
with left:
    st.subheader(f"Ce que {person_a.name} peut donner à {person_b.name}")
    _show_tradeable_table(a_to_b)
with right:
    st.subheader(f"Ce que {person_b.name} peut donner à {person_a.name}")
    _show_tradeable_table(b_to_a)

st.divider()
st.subheader("Appliquer")

if not a_to_b_all or not b_to_a_all:
    st.info("Aucun échange équivalent possible entre ces deux personnes pour l'instant.")
    st.stop()

tab_one, tab_batch = st.tabs(["Un échange", "Session multi-échanges"])

with tab_one:
    if not a_to_b or not b_to_a:
        st.warning("Le filtre actuel masque un des deux côtés de l'échange. Modifie la recherche pour choisir les deux stickers.")
    else:
        pick_left, pick_right = st.columns(2)
        sticker_from_a = pick_left.selectbox(
            f"Sticker donné par {person_a.name}",
            a_to_b,
            format_func=sticker_option_label,
        )
        sticker_from_b = pick_right.selectbox(
            f"Sticker donné par {person_b.name}",
            b_to_a,
            format_func=sticker_option_label,
        )
        confirm_left, confirm_right = st.columns(2)
        with confirm_left:
            st.write(f"{person_a.name} donne à {person_b.name}")
            render_sticker_card(sticker_from_a)
        with confirm_right:
            st.write(f"{person_b.name} donne à {person_a.name}")
            render_sticker_card(sticker_from_b)
        actor_name = st.text_input("Appliqué par", placeholder="Optionnel", key="single_trade_actor")
        confirm = st.checkbox("Je confirme que cet échange 1 contre 1 doit être appliqué.")
        if st.button("Appliquer l'échange", type="primary", disabled=not confirm):
            try:
                with get_session() as session:
                    apply_equivalent_trade(
                        session,
                        person_a.id,
                        person_b.id,
                        sticker_from_a["sticker_id"],
                        sticker_from_b["sticker_id"],
                        actor_name,
                    )
                st.session_state.last_exchange_summary = (
                    f"Échange appliqué: {person_a.name} a donné {sticker_from_a['display_code']} "
                    f"et {person_b.name} a donné {sticker_from_b['display_code']}."
                )
                st.rerun()
            except ValueError as exc:
                st.error(str(exc))

with tab_batch:
    st.caption("Colle les codes donnés par chaque personne. Les deux listes doivent avoir le même nombre de stickers valides.")
    col_a, col_b = st.columns(2)
    raw_a = col_a.text_area(
        f"Stickers donnés par {person_a.name} à {person_b.name}",
        placeholder="MEX1\nBRA14\nFWC3",
        height=180,
    )
    raw_b = col_b.text_area(
        f"Stickers donnés par {person_b.name} à {person_a.name}",
        placeholder="FRA20\nARG7\nFWC5",
        height=180,
    )
    if st.button("Prévisualiser la session d'échanges", type="primary"):
        with get_session() as session:
            st.session_state.exchange_batch_preview = {
                "pair": (person_a.id, person_b.id),
                "preview": preview_batch_equivalent_trades(session, person_a.id, person_b.id, raw_a, raw_b),
            }

    stored = st.session_state.get("exchange_batch_preview")
    if stored and stored.get("pair") == (person_a.id, person_b.id):
        preview = stored["preview"]
        if preview["errors"]:
            st.error("À corriger avant application:\n\n" + "\n".join(f"- {error}" for error in preview["errors"]))
        rows = [
            {
                f"{person_a.name} donne": pair["from_a"]["display_code"],
                f"Sticker {person_a.name}": pair["from_a"]["label"],
                f"{person_b.name} donne": pair["from_b"]["display_code"],
                f"Sticker {person_b.name}": pair["from_b"]["label"],
            }
            for pair in preview["pairs"]
        ]
        if rows:
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True, height=260)
        st.metric("Échanges prêts à appliquer", preview["valid_trade_count"])
        actor_name = st.text_input("Appliqué par", placeholder="Optionnel", key="batch_trade_actor")
        confirm_batch = st.checkbox("Je confirme que toute cette session d'échanges doit être appliquée.")
        if st.button("Appliquer la session d'échanges", disabled=not (preview["can_apply"] and confirm_batch)):
            try:
                with get_session() as session:
                    result = apply_batch_equivalent_trades(
                        session,
                        person_a.id,
                        person_b.id,
                        preview["pairs"],
                        actor_name=actor_name,
                    )
                st.session_state.last_exchange_summary = (
                    f"Session appliquée: {result['trade_count']} échange(s) entre {person_a.name} et {person_b.name}."
                )
                st.session_state.pop("exchange_batch_preview", None)
                st.rerun()
            except ValueError as exc:
                st.error(str(exc))
