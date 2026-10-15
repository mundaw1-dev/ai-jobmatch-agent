"""Shortlist management UI."""
import streamlit as st
from persistence.repositories import load_shortlist, remove_from_shortlist

def render_shortlist():
    st.subheader("Shortlist")
    items = load_shortlist()
    if not items: st.info("No shortlisted jobs yet. Add jobs from Settings or the results page."); return
    for job, notes in items:
        with st.container(border=True):
            st.markdown(f"**{job.title}** — {job.company}")
            if notes: st.write(notes)
            if job.url.startswith(("https://", "http://")): st.link_button("Open advert", job.url)
            if st.button("Remove", key=f"remove_{job.id}"):
                remove_from_shortlist(job.id); st.rerun()
