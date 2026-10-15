
# File: ui/settings.py
# Path: C:\Technative\ai-jobmatch-agent\ui\settings.py
"""Settings, Ollama diagnostics and safe demo-data controls."""

import hashlib

import streamlit as st

from config import (
    OLLAMA_BASE_URL,
    OLLAMA_MODEL,
    OLLAMA_TIMEOUT_SECONDS,
)
from database import initialize_database
from models import JobPosting
from persistence.repositories import (
    add_to_shortlist,
    load_jobs,
    load_shortlist,
    save_jobs,
)
from services.llm import (
    OllamaError,
    test_connection,
)


def _render_ollama_settings() -> None:
    """Display local Ollama settings and provide a connection test."""
    st.markdown("#### Local AI / Ollama")

    st.write(
        "The application can use Ollama to generate optional AI job "
        "assessments. By default, requests go to Ollama on this computer. "
        "When you request an assessment, selected candidate-profile fields "
        "and job details are sent to the configured Ollama server."
    )

    st.write(f"**Ollama URL:** `{OLLAMA_BASE_URL}`")
    st.write(f"**Configured model:** `{OLLAMA_MODEL}`")
    st.write(
        f"**Request timeout:** {OLLAMA_TIMEOUT_SECONDS} seconds"
    )

    if st.button(
        "Test Ollama connection",
        key="test_ollama_connection",
        type="primary",
    ):
        with st.spinner("Checking Ollama..."):
            try:
                status = test_connection()
                st.session_state["ollama_status"] = status
                st.session_state.pop("ollama_status_error", None)
            except OllamaError as exc:
                st.session_state.pop("ollama_status", None)
                st.session_state["ollama_status_error"] = str(exc)
            except Exception:
                st.session_state.pop("ollama_status", None)
                st.session_state["ollama_status_error"] = (
                    "An unexpected error occurred while checking Ollama."
                )

    error = st.session_state.get("ollama_status_error")

    if error:
        st.error(error)

    status = st.session_state.get("ollama_status")

    if status:
        if status.get("available"):
            st.success("Ollama server is responding.")

            if status.get("model_available"):
                st.success(
                    f"Configured model is available: "
                    f"{status.get('configured_model')}"
                )
            else:
                st.warning(
                    f"The configured model '{status.get('configured_model')}' "
                    "was not found in Ollama's model list."
                )

            available_models = status.get("models", [])

            if available_models:
                st.write("**Installed Ollama models:**")
                for model_name in available_models:
                    st.write(f"- {model_name}")
            else:
                st.info(
                    "Ollama responded, but no installed models were listed."
                )


def _render_demo_job_form() -> None:
    """Render the sample-job form and save a validated job."""
    st.markdown("#### Add a sample job")

    with st.form("demo_job"):
        title = st.text_input(
            "Job title",
            value="Healthcare AI Engineer",
        )

        company = st.text_input(
            "Company",
            value="Example Health Data",
        )

        location = st.text_input(
            "Location",
            value="Remote, UK",
        )

        description = st.text_area(
            "Description",
            value=(
                "Python SQL healthcare data engineering "
                "RAG evaluation Azure"
            ),
        )

        rate = st.number_input(
            "Maximum day rate (£, 0 = unknown)",
            min_value=0.0,
            value=500.0,
            step=25.0,
        )

        add = st.form_submit_button(
            "Save sample job",
            type="primary",
        )

    if not add:
        return

    if not title.strip():
        st.error("Enter a job title.")
        return

    if not company.strip():
        st.error("Enter a company name.")
        return

    job_id = "manual-" + hashlib.sha256(
        (
            title.strip()
            + company.strip()
            + description
        ).encode("utf-8")
    ).hexdigest()[:20]

    try:
        job = JobPosting(
            id=job_id,
            title=title.strip(),
            company=company.strip(),
            location=location.strip() or "Unspecified",
            description=description.strip(),
            day_rate_max=rate or None,
            salary_period="day" if rate else "unknown",
            source="manual",
        )

        save_jobs([job])

        st.session_state["last_added_sample_job_id"] = job.id

        st.success(f"Sample job saved: {job.title}")

    except Exception as exc:
        st.error(f"Could not save sample job: {exc}")


def _render_sample_shortlist() -> None:
    """Offer a shortcut to shortlist the most recently saved sample job."""
    st.divider()
    st.markdown("#### Shortlist a sample job")

    last_job_id = st.session_state.get(
        "last_added_sample_job_id"
    )

    if not last_job_id:
        st.caption(
            "Save a sample job first to enable this shortcut."
        )
        return

    jobs = load_jobs()

    sample_job = next(
        (
            job for job in jobs
            if job.id == last_job_id
        ),
        None,
    )

    if sample_job is None:
        st.info(
            "The previously saved sample job could not be found. "
            "Save a sample job again."
        )
        return

    existing_ids = {
        job.id
        for job, _notes in load_shortlist()
    }

    if sample_job.id in existing_ids:
        st.success(f"Already shortlisted: {sample_job.title}")
        return

    if st.button(
        "Shortlist this sample job",
        key="shortlist_added",
        type="primary",
    ):
        try:
            add_to_shortlist(sample_job)
            st.success(f"Added to shortlist: {sample_job.title}")
            st.rerun()
        except Exception as exc:
            st.error(f"Could not shortlist sample job: {exc}")


def _render_database_status() -> None:
    """Show database counts without disrupting other settings."""
    st.divider()
    st.markdown("#### Database status")

    try:
        st.write(f"Stored jobs: {len(load_jobs())}")
        st.write(
            f"Shortlisted jobs: {len(load_shortlist())}"
        )
    except Exception as exc:
        st.warning(
            f"Could not retrieve database statistics: {exc}"
        )


def render_settings() -> None:
    """Render database, Ollama and sample-data settings."""
    st.subheader("Settings")

    st.write(
        "Application data is stored in a local SQLite database. "
        "The application does not send assessment requests automatically. "
        "When you explicitly request an AI assessment, selected profile "
        "and job data are sent to the configured Ollama server."
    )

    if st.button("Initialize / verify database"):
        try:
            initialize_database()
            st.success("Database schema is ready.")
        except Exception as exc:
            st.error(f"Could not initialize the database: {exc}")

    st.divider()

    _render_ollama_settings()

    st.divider()

    _render_demo_job_form()
    _render_sample_shortlist()
    _render_database_status()
