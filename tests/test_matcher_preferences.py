
# File: tests/test_matcher_preferences.py
"""Regression tests for candidate preference-aware matching."""

from models import CandidateProfile, JobPosting
from services.matcher import match_job, rank_jobs
from services.recommendation import recommendation_for


def make_profile(**overrides):
    data = {
        "name": "Test Candidate",
        "summary": (
            "Senior engineer specialising in healthcare and life sciences."
        ),
        "skills": [
            "LLM",
            "RAG",
            "SQL Server",
            "Healthcare data",
            "Python",
        ],
        "preferred_titles": [
            "Senior AI Engineer",
            "Healthcare AI Engineer",
        ],
        "preferred_locations": ["Remote", "United Kingdom"],
        "minimum_day_rate": 450.0,
        "employment_types": ["Permanent", "Contract"],
    }
    data.update(overrides)
    return CandidateProfile(**data)


def make_job(**overrides):
    data = {
        "id": "job-1",
        "title": "Senior AI Engineer",
        "company": "Example Ltd",
        "description": (
            "Build large language model applications using "
            "retrieval-augmented generation and Python for clinical data."
        ),
        "location": "Remote, United Kingdom",
        "employment_type": "Contract",
        "day_rate_min": 500.0,
        "day_rate_max": 600.0,
        "salary_period": "day",
        "salary_currency": "GBP",
        "url": "https://example.com/job-1",
        "source": "test",
    }
    data.update(overrides)
    return JobPosting(**data)


def test_llm_and_rag_aliases_match_advert():
    result = match_job(make_profile(), make_job())

    assert "LLM" in result.matched_skills
    assert "RAG" in result.matched_skills


def test_sql_does_not_match_tsql():
    profile = make_profile(
        skills=["SQL"],
        preferred_titles=[],
        preferred_locations=[],
        employment_types=[],
        minimum_day_rate=None,
    )
    job = make_job(
        title="Database Developer",
        description="Experienced with T-SQL stored procedures.",
        location="London",
        employment_type="Permanent",
        day_rate_min=None,
        day_rate_max=None,
        salary_min=None,
        salary_max=None,
        salary_period="unknown",
    )

    result = match_job(profile, job)

    assert "SQL" not in result.matched_skills


def test_contract_preference_is_scored():
    profile = make_profile()
    contract_job = make_job(employment_type="Contract")
    permanent_job = make_job(
        id="job-2",
        employment_type="Permanent",
    )

    contract_result = match_job(profile, contract_job)
    permanent_result = match_job(profile, permanent_job)

    assert any(
        "employment type matched" in item.lower()
        for item in contract_result.rationale
    )
    assert contract_result.score == permanent_result.score


def test_unpreferred_employment_type_is_penalised():
    profile = make_profile(employment_types=["Permanent"])
    permanent_job = make_job(employment_type="Permanent")
    freelance_job = make_job(
        id="job-2",
        employment_type="Freelance",
    )

    assert match_job(profile, permanent_job).score > match_job(
        profile, freelance_job
    ).score


def test_healthcare_advert_receives_relevance_points():
    profile = make_profile()
    healthcare_job = make_job(
        description="Build clinical data RAG applications for life sciences."
    )
    generic_job = make_job(
        id="job-2",
        description="Build internal reporting applications."
    )

    assert match_job(profile, healthcare_job).score > match_job(
        profile, generic_job
    ).score


def test_annual_salary_is_not_treated_as_day_rate():
    profile = make_profile()
    job = make_job(
        day_rate_min=None,
        day_rate_max=None,
        salary_min=60000,
        salary_max=80000,
        salary_period="year",
    )

    result = match_job(profile, job)

    assert any("Rate unknown" in item for item in result.rationale)


def test_matching_score_is_bounded():
    result = match_job(make_profile(), make_job())

    assert 0 <= result.score <= 100


def test_ranking_is_deterministic():
    profile = make_profile()
    jobs = [
        make_job(id="job-b", title="Senior AI Engineer"),
        make_job(id="job-a", title="Senior AI Engineer"),
    ]

    first = [result.job.id for result in rank_jobs(profile, jobs)]
    second = [result.job.id for result in rank_jobs(profile, jobs)]

    assert first == second


def test_recommendation_includes_heuristic_disclaimer():
    result = match_job(make_profile(), make_job())

    recommendation = recommendation_for(result)

    assert "not a probability" in recommendation
    assert "Relevant skills:" in recommendation
