from __future__ import annotations

import pandas as pd
import streamlit as st


def render_dataframe(rows, height: int = 520) -> None:
    data = pd.DataFrame(rows)
    if data.empty:
        st.caption("Aucun résultat.")
        return
    st.dataframe(data, use_container_width=True, hide_index=True, height=height)

