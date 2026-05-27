from __future__ import annotations

from datetime import datetime
from pathlib import Path

import streamlit as st

from src.config import DATA_DIR
from src.db import get_session
from src.services.excel_import import preview_excel, save_uploaded_file
from src.services.export_service import export_csv, export_excel
from src.services.import_service import run_excel_import, run_source_names_import
from src.ui.components import ensure_db


ensure_db()
st.title("Import / Export")

tab_import, tab_names, tab_export = st.tabs(["Import Excel", "Noms stickers", "Export"])

with tab_import:
    st.subheader("Importer l'Excel")
    uploaded = st.file_uploader("Fichier Excel", type=["xlsx", "xlsm"])
    source_path = st.text_input("Ou chemin local", value="source_excel.xlsx")
    path: Path | None = None
    if uploaded:
        path = save_uploaded_file(uploaded, DATA_DIR / "input")
        st.success(f"Fichier uploadé: {path}")
    elif source_path:
        candidate = Path(source_path)
        if candidate.exists():
            path = candidate
    if path and st.button("Prévisualiser"):
        try:
            preview = preview_excel(path)
            st.write(
                {
                    "feuille": preview.sheet_name,
                    "stickers": preview.sticker_count,
                    "personnes": preview.people_names,
                    "lignes_ignorées": len(preview.ignored_rows),
                }
            )
        except Exception as exc:
            st.error(str(exc))
    if path and st.button("Lancer l'import complet", type="primary"):
        try:
            with get_session() as session:
                result = run_excel_import(session, path)
            st.success("Import terminé.")
            st.write(result)
        except Exception as exc:
            st.error(str(exc))

with tab_names:
    st.subheader("Importer les noms depuis source_names.txt")
    st.caption("Source locale fixe pour les labels, noms de joueurs, équipes et flags foil/team photo/emblem.")
    source_names_path = st.text_input("Chemin source_names", value="source_names.txt")
    if st.button("Importer les noms", type="primary"):
        try:
            with get_session() as session:
                result = run_source_names_import(session, source_names_path)
            st.success("Noms importés.")
            st.write(result)
        except Exception as exc:
            st.error(str(exc))

with tab_export:
    st.subheader("Exporter l'état courant")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    csv_path = DATA_DIR / "exports" / f"panini_export_{timestamp}.csv"
    xlsx_path = DATA_DIR / "exports" / f"panini_export_{timestamp}.xlsx"
    c1, c2 = st.columns(2)
    if c1.button("Générer CSV"):
        with get_session() as session:
            path = export_csv(session, csv_path)
        st.success(f"CSV généré: {path}")
        st.download_button("Télécharger CSV", path.read_bytes(), file_name=path.name, mime="text/csv")
    if c2.button("Générer Excel"):
        with get_session() as session:
            path = export_excel(session, xlsx_path)
        st.success(f"Excel généré: {path}")
        st.download_button(
            "Télécharger Excel",
            path.read_bytes(),
            file_name=path.name,
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
