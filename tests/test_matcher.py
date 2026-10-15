
# tests/test_matcher.py

import pytest
from pydantic import ValidationError

from models import CandidateProfile, JobPosting
from services.matcher import match_job, rank_jobs


def test_match_is_bounded_and_explainable():
    profile = CandidateProfile(skills=["Python", "SQL", "RAG"])
    job = JobPosting(
        id="1",
        title="AI Engineer",
        description="Python SQL healthcare RAG",
    )

    result = match_job(profile, job)

    assert result.score == 82.5
    assert set(result.matched_skills) == {"Python", "SQL", "RAG"}
    assert result.rationale


def test_rank_orders_best_first():
    profile = CandidateProfile(skills=["Python"])
    jobs = [
        JobPosting(id="a", title="A", description="none"),
        JobPosting(id="b", title="B", description="Python"),
    ]

    assert rank_jobs(profile, jobs)[0].job.id == "b"


def test_minimum_rate_penalty():
    profile = CandidateProfile(
        skills=["Python"],
        minimum_day_rate=500,
    )
    job = JobPosting(
        id="1",
        title="Engineer",
        description="Python",
        day_rate_max=400,
    )

    result = match_job(profile, job)

    assert "below the minimum" in " ".join(result.rationale)


def test_annual_salary_does_not_count_as_day_rate():
    profile = CandidateProfile(
        skills=["Python"],
        minimum_day_rate=500,
    )
    job = JobPosting(
        id="annual-1",
        title="Python Engineer",
        description="Annual salary",
        salary_min=60000,
        salary_max=60000,
        salary_period="year",
    )

    result = match_job(profile, job)

    assert any(
        "missing or below" in reason
        for reason in result.rationale
    )


def test_daily_salary_can_match_minimum():
    profile = CandidateProfile(minimum_day_rate=500)
    job = JobPosting(
        id="daily-1",
        title="Contract Engineer",
        salary_min=550,
        salary_max=600,
        salary_period="day",
        salary_currency="GBP",
    )

    result = match_job(profile, job)

    assert any(
        "meets the minimum" in reason
        for reason in result.rationale
    )


def test_non_gbp_rate_does_not_confirm_match():
    profile = CandidateProfile(minimum_day_rate=500)
    job = JobPosting(
        id="usd-1",
        title="Engineer",
        day_rate_max=800,
        salary_currency="USD",
    )

    result = match_job(profile, job)

    assert any(
        "missing or below" in reason
        for reason in result.rationale
    )


def test_skill_matching_uses_token_boundaries():
    profile = CandidateProfile(skills=["SQL"])
    job = JobPosting(
        id="boundary-1",
        title="Developer",
        description="Experience with NoSQL databases",
    )

    result = match_job(profile, job)

    assert "SQL" not in result.matched_skills
    assert "SQL" in result.missing_skills


def test_existing_manual_day_rate_still_works():
    profile = CandidateProfile(minimum_day_rate=450)
    job = JobPosting(
        id="manual-1",
        title="Data Engineer",
        day_rate_min=450,
        day_rate_max=500,
    )

    result = match_job(profile, job)

    assert any(
        "meets the minimum" in reason
        for reason in result.rationale
    )


def test_invalid_salary_range_is_rejected():
    with pytest.raises(ValidationError):
        JobPosting(
            id="invalid-1",
            title="Engineer",
            salary_min=700,
            salary_max=500,
            salary_period="day",
        )
