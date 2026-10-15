
# tests/test_matcher_regressions.py

from models import CandidateProfile, JobPosting
from services.matcher import match_job, rank_jobs


def make_job(**overrides):
    values = {
        "id": "test-1",
        "title": "AI Engineer",
        "company": "Example Ltd",
        "description": "Python, SQL and large language models",
        "location": "Remote UK",
    }
    values.update(overrides)
    return JobPosting(**values)


def test_llm_matches_large_language_models():
    profile = CandidateProfile(skills=["LLM"])
    result = match_job(profile, make_job())

    assert result.matched_skills == ["LLM"]
    assert result.missing_skills == []


def test_sql_does_not_match_tsql():
    profile = CandidateProfile(skills=["SQL"])
    job = make_job(description="Experience with T-SQL required")

    result = match_job(profile, job)

    assert result.matched_skills == []
    assert result.missing_skills == ["SQL"]


def test_tsql_matches_tsql():
    profile = CandidateProfile(skills=["T-SQL"])
    job = make_job(description="Experience with T-SQL required")

    result = match_job(profile, job)

    assert result.matched_skills == ["T-SQL"]


def test_missing_day_rate_is_unknown_not_zero():
    profile = CandidateProfile(
        skills=["Python"],
        minimum_day_rate=450,
    )
    job = make_job(description="Python engineering")

    result = match_job(profile, job)

    assert any("Rate unknown" in item for item in result.rationale)
    assert result.score > 0


def test_insufficient_advertised_rate_is_penalised():
    profile = CandidateProfile(
        skills=["Python"],
        minimum_day_rate=450,
    )
    job = make_job(
        day_rate_min=350,
        day_rate_max=400,
    )

    result = match_job(profile, job)

    assert any("below the" in item for item in result.rationale)


def test_seniority_difference_does_not_prevent_title_match():
    profile = CandidateProfile(
        preferred_titles=["AI Engineer"],
    )
    job = make_job(title="Senior AI Engineer")

    result = match_job(profile, job)

    assert any("Preferred title matched" in item for item in result.rationale)


def test_remote_location_preference_matches_remote_advert():
    profile = CandidateProfile(
        preferred_locations=["Remote"],
    )
    job = make_job(location="Remote, United Kingdom")

    result = match_job(profile, job)

    assert any("Location preference matched" in item for item in result.rationale)


def test_ranking_is_deterministic():
    profile = CandidateProfile(skills=["Python"])
    jobs = [
        make_job(id="b", title="Zeta Engineer"),
        make_job(id="a", title="Alpha Engineer"),
    ]

    first = rank_jobs(profile, jobs)
    second = rank_jobs(profile, jobs)

    assert [(r.job.id, r.score) for r in first] == [
        (r.job.id, r.score) for r in second
    ]
