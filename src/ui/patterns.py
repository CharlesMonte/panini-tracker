from __future__ import annotations

import html

import pandas as pd
import streamlit as st


def sticker_name(row: dict) -> str:
    return row.get("player_name") or row.get("label") or row.get("display_code") or row.get("sticker_code") or ""


def sticker_context(row: dict) -> str:
    return row.get("team_name") or row.get("category_name") or row.get("category_code") or ""


def sticker_option_label(row: dict) -> str:
    context = sticker_context(row)
    suffix = f" - {context}" if context and context not in sticker_name(row) else ""
    return f"{row.get('display_code')} - {sticker_name(row)}{suffix}"


def render_sticker_card(row: dict, caption: str | None = None) -> None:
    code = html.escape(str(row.get("display_code") or row.get("sticker_code") or ""))
    title = html.escape(sticker_name(row))
    context = html.escape(sticker_context(row))
    caption_html = f" · {html.escape(caption)}" if caption else ""
    st.markdown(
        f"""
        <div class="panini-card">
          <div style="font-size: 0.85rem; opacity: 0.75;">{code}{caption_html}</div>
          <div style="font-size: 1.25rem; font-weight: 700; margin-top: 0.15rem;">{title}</div>
          <div style="opacity: 0.8; margin-top: 0.1rem;">{context}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def compact_sticker_dataframe(rows: list[dict], quantity_label: str | None = None) -> pd.DataFrame:
    result = []
    for row in rows:
        display = {
            "Code": row.get("display_code"),
            "Sticker": sticker_name(row),
            "Équipe / catégorie": sticker_context(row),
        }
        if quantity_label:
            display[quantity_label] = row.get("giver_quantity") or row.get("seller_quantity") or row.get("quantity")
        result.append(display)
    return pd.DataFrame(result)


def show_compact_table(data: pd.DataFrame, height: int = 420) -> None:
    if data.empty:
        st.caption("Aucun résultat.")
        return
    column_config = {
        "Code": st.column_config.TextColumn("Code", width="small"),
        "Sticker": st.column_config.TextColumn("Sticker", width="large"),
        "Équipe / catégorie": st.column_config.TextColumn("Équipe / catégorie", width="medium"),
    }
    for column in data.columns:
        if column not in column_config:
            column_config[column] = st.column_config.NumberColumn(column, width="small")
    st.dataframe(data, use_container_width=True, hide_index=True, height=height, column_config=column_config)

