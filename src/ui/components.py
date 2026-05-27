from __future__ import annotations

import pandas as pd
import streamlit as st

from src.db import get_session, init_db
from src.repositories import get_people, get_stickers


def ensure_db() -> None:
    init_db()


def people_options():
    with get_session() as session:
        return get_people(session)


def sticker_categories():
    with get_session() as session:
        return sorted({s.category_code for s in get_stickers(session) if s.category_code})


def render_empty_import_hint() -> None:
    st.info("Aucune donnée détectée. Importez d'abord le fichier Excel dans la page Import / Export.")


def df(rows) -> pd.DataFrame:
    if isinstance(rows, pd.DataFrame):
        return rows
    return pd.DataFrame(rows)


def show_table(rows, height: int = 520) -> None:
    data = df(rows)
    if data.empty:
        st.caption("Aucun résultat.")
    else:
        st.dataframe(data, use_container_width=True, hide_index=True, height=height)

