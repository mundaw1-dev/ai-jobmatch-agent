
# File: ui/results.py
# Path: C:\Technative\ai-jobmatch-agent\ui\results.py
"""Results tab with explainable scores, AI assessments and shortlist actions."""

import streamlit as st

from graph.workflow import run_matching
from persistence.repositories import (
    add_to_shortlist,
    load_jobs,
    load_profile,
    load_shortlist,
)
from services.llm import (
    JobAssessment,
    OllamaError,
    assess_match,
)
from services.recommendation import recommendation_for


def _render_ai_assessment(assessment: JobAssessment) -> None:
    """Render a validated AI assessment in readable sections."""
    st.markdown("#### Overall assessment")
    st.write(assessment.overall_assessment)

    st.markdown("#### Strengths")

    if assessment.strengths:
        for item in assessment.strengths:
            st.markdown(f"- **{item.statement}**")
            st.caption(f"Evidence: {item.evidence}")
    else:
        st.write("No strengths were identified from the supplied evidence.")

    st.markdown("#### Gaps to investigate")

    if assessment.gaps:
        for item in assessment.gaps:
            st.markdown(f"- **{item.statement}**")
            st.caption(f"Evidence: {item.evidence}")
    else:
        st.write("No specific gaps were established from the supplied data.")

    st.markdown("#### Questions to verify")

    if assessment.questions_to_verify:
        for question in assessment.questions_to_verify:
            st.markdown(f"- {question}")
    else:
        st.write("No additional questions were suggested.")

    st.markdown("#### AI recommendation")
    st.write(assessment.recommendation)

    st.markdown("#### Uncertainty")
    st.write(assessment.uncertainty)

    st.caption(
        "This is an LLM-generated assessment, not a verified fact or "
        "a prediction of hiring success. Check the original advert."
    )


def render_results() -> None:
    """Render matching results and allow AI assessments and shortlisting."""
    st.subheader("Match results")

    profile = load_profile()
    jobs = load_jobs()

    if not profile:
        st.warning("Create and save a profile first.")
        return

    if not jobs:
        st.info(
            "Search jobs or add a sample job under Settings first."
        )
        return

    try:
        results = run_matching(profile, jobs)
    except (ValueError, TypeError) as exc:
        st.error(f"Could not calculate job matches: {exc}")
        return

    if not results:
        st.info("No jobs to match.")
        return

    shortlisted_ids = {
        job.id
        for job, _notes in load_shortlist()
    }

    for result in results:
        job = result.job
        assessment_key = f"llm_assessment_{job.id}"

        with st.container(border=True):
            st.markdown(f"**{job.title}** — {job.company}")

            st.caption(
                f"{job.location} · {job.employment_type} "
                f"· Source: {job.source}"
            )

            st.progress(
                max(0, min(100, int(result.score))),
                text=(
                    f"Deterministic match score: {result.score:.1f}/100 "
                    "(heuristic, not a probability)"
                ),
            )

            st.write(recommendation_for(result))

            if result.matched_skills:
                st.write(
                    "**Matched skills:** "
                    + ", ".join(result.matched_skills)
                )

            if result.missing_skills:
                st.write(
                    "**Other profile skills not found in advert:** "
                    + ", ".join(result.missing_skills)
                )

            st.write("**Scoring evidence**")

            for item in result.rationale:
                st.write(f"- {item}")

            if job.url.startswith(("https://", "http://")):
                st.link_button(
                    "Open original advert",
                    job.url,
                )

            st.divider()
            st.markdown("#### Local AI assessment")

            st.caption(
                "Uses your configured Ollama model to assess this job "
                "against your saved profile. The AI assessment does not "
                "change the deterministic match score."
            )

            if st.button(
                "Generate local AI assessment",
                key=f"assess_{job.id}",
                type="secondary",
            ):
                with st.spinner(
                    "Asking your local Ollama model to assess this job..."
                ):
                    try:
                        assessment = assess_match(profile, result)
                        st.session_state[assessment_key] = (
                            assessment.model_dump()
                        )
                        st.session_state.pop(
                            f"{assessment_key}_error",
                            None,
                        )
                    except OllamaError as exc:
                        st.session_state[
                            f"{assessment_key}_error"
                        ] = str(exc)
                    except Exception:
                        st.session_state[
                            f"{assessment_key}_error"
                        ] = (
                            "An unexpected error occurred while generating "
                            "the assessment. Check the application logs."
                        )

            assessment_error = st.session_state.get(
                f"{assessment_key}_error"
            )

            if assessment_error:
                st.error(
                    "The AI assessment could not be generated: "
                    f"{assessment_error}"
                )

            saved_assessment = st.session_state.get(assessment_key)

            if saved_assessment:
                try:
                    assessment = JobAssessment.model_validate(
                        saved_assessment
                    )
                    with st.expander(
                        "View AI assessment",
                        expanded=True,
                    ):
                        _render_ai_assessment(assessment)
                except Exception:
                    st.session_state.pop(assessment_key, None)
                    st.warning(
                        "The saved assessment could not be displayed. "
                        "Generate it again."
                    )

            st.divider()

            if job.id in shortlisted_ids:
                st.success("Already shortlisted")
            elif st.button(
                "Shortlist job",
                key=f"shortlist_{job.id}",
                type="primary",
            ):
                try:
                    add_to_shortlist(job)
                    st.session_state["shortlist_message"] = (
                        f"Shortlisted: {job.title}"
                    )
                    st.rerun()
                except Exception as exc:
                    st.error(
                        f"Could not shortlist this job: {exc}"
                    )

    message = st.session_state.pop(
        "shortlist_message",
        None,
    )

    if message:
        st.success(message)
