"""Job detail presentation helper."""
import streamlit as st
from models import JobPosting

def render_job_detail(job: JobPosting):
    st.markdown(f"### {job.title}")
    st.write(f"**Company:** {job.company}  |  **Location:** {job.location}")
    st.write(job.description or "No description supplied.")
    if job.url.startswith(("https://", "http://")): st.link_button("Open original advert", job.url)
