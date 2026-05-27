from __future__ import annotations

import pandas as pd
import streamlit as st

from src.config import settings
from src.db import get_session
from src.repositories import get_people
from src.services.exchange_service import apply_batch_sales, apply_sale, get_sale_candidates, preview_batch_sales
from src.ui.components import ensure_db, render_empty_import_hint
from src.ui.patterns import render_sticker_card, sticker_option_label
from src.utils.normalization import normalize_search_text


ensure_db()
st.title("Achats / ventes")
st.caption(f"Prix indicatif: {settings.sale_price:.2f} € par carte. Le paiement reste hors application.")

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
                    row["label"] or "",
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
                "Catégorie": row.get("category_code"),
                "Quantité vendeur": row["seller_quantity"],
                "Reste après vente": row["seller_keeps_after_sale"],
                "Prix indicatif": f"{row['price']:.2f} €",
            }
            for row in rows
        ]
    )


def _show_sales_table(rows: list[dict]) -> None:
    data = _display_rows(rows)
    if data.empty:
        st.caption("Aucune opportunité pour ce binôme.")
        return
    st.dataframe(
        data,
        use_container_width=True,
        hide_index=True,
        height=440,
        column_config={
            "Code": st.column_config.TextColumn("Code", width="small"),
            "Sticker": st.column_config.TextColumn("Sticker", width="large"),
            "Catégorie": st.column_config.TextColumn("Catégorie", width="small"),
            "Quantité vendeur": st.column_config.NumberColumn("Quantité vendeur", width="small"),
            "Reste après vente": st.column_config.NumberColumn("Reste après vente", width="small"),
            "Prix indicatif": st.column_config.TextColumn("Prix indicatif", width="small"),
        },
    )


if "sale_seller_id" not in st.session_state:
    st.session_state.sale_seller_id = people[0].id
if "sale_buyer_id" not in st.session_state:
    st.session_state.sale_buyer_id = people[1].id if len(people) > 1 else people[0].id

people_ids = {person.id for person in people}
qp_pair = (_query_int("seller_id"), _query_int("buyer_id"))
if (
    qp_pair[0] in people_ids
    and qp_pair[1] in people_ids
    and qp_pair[0] != qp_pair[1]
    and st.session_state.get("sale_prefill_pair") != qp_pair
):
    st.session_state.sale_seller_id, st.session_state.sale_buyer_id = qp_pair
    st.session_state.sale_prefill_pair = qp_pair

def _index_for(person_id: int) -> int:
    return next((idx for idx, person in enumerate(people) if person.id == person_id), 0)


c1, c2, c3 = st.columns([1, 1, 0.35])
seller = c1.selectbox("Vendeur", people, index=_index_for(st.session_state.sale_seller_id), format_func=lambda p: p.name)
buyer = c2.selectbox("Acheteur", people, index=_index_for(st.session_state.sale_buyer_id), format_func=lambda p: p.name)
st.session_state.sale_seller_id = seller.id
st.session_state.sale_buyer_id = buyer.id
if c3.button("Inverser"):
    st.session_state.sale_seller_id, st.session_state.sale_buyer_id = buyer.id, seller.id
    st.rerun()

if st.session_state.get("last_sale_summary"):
    st.success(st.session_state.pop("last_sale_summary"))

if seller.id == buyer.id:
    st.warning("Choisis deux personnes différentes pour préparer un achat/vente.")
    st.stop()

search = st.text_input("Filtrer les stickers", placeholder="Code, joueur, équipe, catégorie...")

with get_session() as session:
    all_rows = get_sale_candidates(session, seller_id=seller.id, buyer_id=buyer.id)

rows = _filter_rows(all_rows, search)

m1, m2, m3 = st.columns(3)
m1.metric("Stickers vendables", len(all_rows))
m2.metric("Prix unitaire", f"{settings.sale_price:.2f} €")
m3.metric("Total si tout vendu", f"{len(all_rows) * settings.sale_price:.2f} €")

st.subheader(f"Ce que {seller.name} peut vendre à {buyer.name}")
_show_sales_table(rows)

st.divider()
st.subheader("Acter")

if not all_rows:
    st.info("Aucune vente possible entre ces deux personnes pour l'instant.")
    st.stop()

tab_one, tab_batch = st.tabs(["Une vente", "Session multi-ventes"])

with tab_one:
    if not rows:
        st.warning("Le filtre actuel masque toutes les ventes possibles. Modifie la recherche pour choisir un sticker.")
    else:
        selected = st.selectbox("Sticker vendu", rows, format_func=sticker_option_label)
        st.write(f"{seller.name} vend à {buyer.name} pour un prix indicatif de {selected['price']:.2f} €")
        render_sticker_card(selected)
        actor_name = st.text_input("Acté par", placeholder="Optionnel", key="single_sale_actor")
        confirm = st.checkbox("Je confirme que cette vente doit être appliquée.")
        if st.button("Appliquer la vente", type="primary", disabled=not confirm):
            try:
                with get_session() as session:
                    apply_sale(
                        session,
                        seller_id=seller.id,
                        buyer_id=buyer.id,
                        sticker_id=selected["sticker_id"],
                        actor_name=actor_name,
                        price=selected["price"],
                    )
                st.session_state.last_sale_summary = (
                    f"Vente appliquée. {seller.name} garde {selected['seller_keeps_after_sale']} exemplaire(s), "
                    f"{buyer.name} possède maintenant ce sticker."
                )
                st.rerun()
            except ValueError as exc:
                st.error(str(exc))

with tab_batch:
    st.caption(f"Colle les codes vendus par {seller.name} à {buyer.name}. Chaque code valide applique une vente à {settings.sale_price:.2f} €.")
    raw_codes = st.text_area("Stickers vendus", placeholder="MEX1\nBRA14\nFWC3", height=180)
    if st.button("Prévisualiser la session de ventes", type="primary"):
        with get_session() as session:
            st.session_state.sale_batch_preview = {
                "pair": (seller.id, buyer.id),
                "preview": preview_batch_sales(session, seller.id, buyer.id, raw_codes),
            }

    stored = st.session_state.get("sale_batch_preview")
    if stored and stored.get("pair") == (seller.id, buyer.id):
        preview = stored["preview"]
        if preview["errors"]:
            st.error("À corriger avant application:\n\n" + "\n".join(f"- {error}" for error in preview["errors"]))
        rows_preview = [
            {
                "Code": item["display_code"],
                "Sticker": item["label"],
                "Prix": f"{item['price']:.2f} €",
                "Reste vendeur": item["seller_keeps_after_sale"],
            }
            for item in preview["valid_items"]
        ]
        if rows_preview:
            st.dataframe(pd.DataFrame(rows_preview), use_container_width=True, hide_index=True, height=260)
        c1, c2 = st.columns(2)
        c1.metric("Ventes prêtes", preview["valid_sale_count"])
        c2.metric("Total indicatif", f"{preview['total_price']:.2f} €")
        actor_name = st.text_input("Acté par", placeholder="Optionnel", key="batch_sale_actor")
        confirm_batch = st.checkbox("Je confirme que toute cette session de ventes doit être appliquée.")
        if st.button("Appliquer la session de ventes", disabled=not (preview["can_apply"] and confirm_batch)):
            try:
                with get_session() as session:
                    result = apply_batch_sales(
                        session,
                        seller.id,
                        buyer.id,
                        preview["items"],
                        actor_name=actor_name,
                    )
                st.session_state.last_sale_summary = (
                    f"Session appliquée: {result['sale_count']} vente(s), total indicatif {result['total_price']:.2f} €."
                )
                st.session_state.pop("sale_batch_preview", None)
                st.rerun()
            except ValueError as exc:
                st.error(str(exc))
