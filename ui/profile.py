
# File: ui/profile.py
"""Candidate profile UI, CV extraction, and profile persistence."""

import streamlit as st

from config import MAX_UPLOAD_MB
from models import CandidateProfile
from persistence.repositories import load_profile, save_profile
from services.candidate_profile import build_candidate_profile
from services.cv_parser import parse_cv_bytes
from services.profile_builder import build_profile


def _split_csv(value: str) -> list[str]:
    """Convert comma-separated input into unique, trimmed values."""
    values = [item.strip() for item in value.split(",") if item.strip()]
    return list(dict.fromkeys(values))


def _profile_form_data(
    profile: CandidateProfile,
) -> dict:
    """Convert a profile to data suitable for the Streamlit form."""
    return profile.model_dump()


def render_profile() -> None:
    """Render the candidate profile page."""
    st.subheader("Candidate profile")

    current = load_profile() or CandidateProfile()

    # Load recommended defaults without immediately overwriting SQLite.
    if st.button("Load recommended CV profile defaults"):
        st.session_state["profile_form"] = _profile_form_data(
            build_candidate_profile()
        )
        st.rerun()

    upload = st.file_uploader(
        "Upload CV (PDF, DOCX, TXT)",
        type=["pdf", "docx", "txt"],
        key="cv_upload",
    )

    if upload and st.button("Extract profile from CV"):
        try:
            cv_text = parse_cv_bytes(
                upload.name,
                upload.getvalue(),
                MAX_UPLOAD_MB * 1024 * 1024,
            )

            extracted = build_profile(cv_text)
            st.session_state["profile_form"] = _profile_form_data(extracted)

            st.success(
                "Profile extracted. Review the fields and save when ready."
            )
            st.rerun()

        except ValueError as exc:
            st.error(str(exc))

    data = st.session_state.get(
        "profile_form",
        _profile_form_data(current),
    )

    with st.form("profile_form_ui"):
        name = st.text_input(
            "Name / profile label",
            value=data.get("name", "Candidate"),
        )

        summary = st.text_area(
            "Summary",
            value=data.get("summary", ""),
            height=130,
        )

        skills = st.text_area(
            "Skills (comma separated)",
            value=", ".join(data.get("skills", [])),
            height=110,
        )

        titles = st.text_input(
            "Preferred job titles (comma separated)",
            value=", ".join(data.get("preferred_titles", [])),
        )

        locations = st.text_input(
            "Preferred locations (comma separated)",
            value=", ".join(data.get("preferred_locations", [])),
        )

        employment_types = st.text_input(
            "Employment types (comma separated)",
            value=", ".join(data.get("employment_types", [])),
            help="For example: Permanent, Contract",
        )

        rate = st.number_input(
            "Minimum day rate (£, 0 = not specified)",
            min_value=0.0,
            value=float(data.get("minimum_day_rate") or 0),
            step=25.0,
        )

        years = st.number_input(
            "Years of experience (0 = unknown)",
            min_value=0.0,
            max_value=80.0,
            value=float(data.get("years_experience") or 0),
            step=1.0,
        )

        submitted = st.form_submit_button(
            "Save profile",
            type="primary",
        )

    if submitted:
        try:
            profile = CandidateProfile(
                name=name.strip() or "Candidate",
                summary=summary[:5000],
                skills=_split_csv(skills),
                preferred_titles=_split_csv(titles),
                preferred_locations=_split_csv(locations),
                employment_types=_split_csv(employment_types),
                minimum_day_rate=rate or None,
                years_experience=years or None,
            )

            # Preserve the existing SQLite persistence mechanism.
            save_profile(profile)

            st.session_state["profile_form"] = _profile_form_data(profile)
            st.success("Profile saved locally.")

        except (ValueError, TypeError) as exc:
            st.error(f"Could not save profile: {exc}")
