
# File: tests/test_candidate_profile.py
"""Tests for the structured candidate profile."""

from models import CandidateProfile
from services.candidate_profile import (
    PREFERRED_SKILLS,
    PREFERRED_TITLES,
    SKILL_ALIASES,
    build_candidate_profile,
)


def test_profile_uses_existing_pydantic_schema():
    profile = build_candidate_profile()

    assert isinstance(profile, CandidateProfile)
    assert profile.name == "Will Munda"


def test_profile_has_ai_and_healthcare_skills():
    profile = build_candidate_profile()
    skills = {skill.casefold() for skill in profile.skills}

    assert "python" in skills
    assert "rag" in skills
    assert "snowflake" in skills
    assert "clinical data" in skills
    assert "omop" in skills


def test_profile_has_preferred_job_titles():
    profile = build_candidate_profile()

    assert "Senior AI Engineer" in profile.preferred_titles
    assert "Forward-Deployed Engineer" in profile.preferred_titles
    assert "Healthcare Data Engineer" in profile.preferred_titles


def test_profile_supports_remote_first_search():
    profile = build_candidate_profile()

    assert "Remote" in profile.preferred_locations
    assert "United Kingdom" in profile.preferred_locations


def test_profile_supports_permanent_and_contract():
    profile = build_candidate_profile()

    assert "Permanent" in profile.employment_types
    assert "Contract" in profile.employment_types


def test_profile_has_minimum_day_rate():
    profile = build_candidate_profile()

    assert profile.minimum_day_rate == 450.0


def test_years_experience_is_not_guessed():
    profile = build_candidate_profile()

    assert profile.years_experience is None


def test_aliases_include_common_llm_and_rag_terms():
    assert "large language models" in SKILL_ALIASES["LLM"]
    assert (
        "retrieval-augmented generation"
        in SKILL_ALIASES["RAG"]
    )


def test_profile_skills_and_titles_are_non_empty():
    profile = build_candidate_profile()

    assert profile.skills
    assert profile.preferred_titles
    assert PREFERRED_SKILLS
    assert PREFERRED_TITLES
