from __future__ import annotations

import streamlit as st


def apply_theme() -> None:
    st.markdown(
        """
        <style>
        .block-container {padding-top: 1.4rem; padding-bottom: 2rem;}
        div[data-testid="stMetric"] {
            background: var(--secondary-background-color);
            color: var(--text-color);
            border: 1px solid rgba(128, 128, 128, 0.24);
            border-radius: 8px;
            padding: 14px 16px;
            box-shadow: 0 1px 2px rgba(0, 0, 0, 0.08);
        }
        div[data-testid="stMetric"] label,
        div[data-testid="stMetric"] [data-testid="stMetricValue"],
        div[data-testid="stMetric"] [data-testid="stMetricDelta"] {
            color: var(--text-color);
        }
        .panini-card {
            border: 1px solid rgba(128, 128, 128, 0.24);
            border-radius: 8px;
            padding: 14px 16px;
            background: var(--secondary-background-color);
            color: var(--text-color);
        }
        .muted {color: rgba(128, 128, 128, 0.95); font-size: 0.9rem;}
        </style>
        """,
        unsafe_allow_html=True,
    )
