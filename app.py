
# File: D:\Technative\ai-jobmatch-agent\app.py

"""Streamlit entry point for AI JobMatch Agent with local authentication."""

import streamlit as st

from auth import render_auth_gate
from database import initialize_database
from ui.profile import render_profile
from ui.search import render_search
from ui.results import render_results
from ui.shortlist import render_shortlist
from ui.settings import render_settings


st.set_page_config(
    page_title="AI JobMatch Agent",
    page_icon="🎯",
    layout="wide",
)

# Preserve the existing application database and initialize its schema.
initialize_database()

# Do not render application pages until the user has authenticated.
if not render_auth_gate():
    st.stop()

st.title("AI JobMatch Agent")
st.caption("Local-first CV profiling and explainable job matching")

st.warning(
    "Match scores are transparent heuristics, not hiring decisions or "
    "probabilities. Always verify the original job advert."
)

tabs = st.tabs(
    [
        "Profile",
        "Search",
        "Results",
        "Shortlist",
        "Settings",
    ]
)

with tabs[0]:
    render_profile()

with tabs[1]:
    render_search()

with tabs[2]:
    render_results()

with tabs[3]:
    render_shortlist()

with tabs[4]:
    render_settings()
