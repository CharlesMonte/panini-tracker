from __future__ import annotations

import streamlit as st

from src.db import init_db
from src.ui.theme import apply_theme


st.set_page_config(page_title="Panini Tracker", page_icon="🏆", layout="wide")
apply_theme()
init_db()

pages = {
    "Usage courant": [
        st.Page("views/1_🏠_Dashboard.py", title="Dashboard", icon="🏠", url_path="Dashboard"),
        st.Page("views/2_📦_Ajouter_des_stickers.py", title="Saisie rapide", icon="📦", url_path="Ajouter"),
        st.Page("views/3_👤_Collection.py", title="Collection", icon="👤", url_path="Collection"),
        st.Page("views/4_🔁_Echanges.py", title="Echanges", icon="🔁", url_path="Echanges"),
        st.Page("views/5_💶_Achats_Ventes.py", title="Achats / Ventes", icon="💶", url_path="Achats-Ventes"),
        st.Page("views/6_🔎_Catalogue.py", title="Catalogue", icon="🔎", url_path="Catalogue"),
    ],
    "Administration": [
        st.Page("views/8_⚙️_Import_Export.py", title="Import / Export", icon="⚙️", url_path="Import-Export"),
        st.Page("views/7_📜_Historique.py", title="Historique", icon="📜", url_path="Historique"),
        st.Page("views/9_🛠️_Admin_DB.py", title="Admin DB", icon="🛠️", url_path="Admin-DB"),
    ],
}

navigation = st.navigation(pages, position="sidebar")
navigation.run()
