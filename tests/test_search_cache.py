
# tests/test_search_cache.py

"""Tests for persistent search caching."""

import json
from datetime import datetime, timedelta, timezone

import database
from models import JobPosting
from persistence.search_cache import (
    clear_search_cache,
    get_cached_jobs,
    get_search_cache_stats,
    make_search_cache_key,
    save_cached_jobs,
)


def make_job(job_id="job-1"):
    return JobPosting(
        id=job_id,
        title="AI Engineer",
        company="Example Ltd",
        description="Python, SQL and healthcare AI engineering.",
        location="Remote, United Kingdom",
        employment_type="Contract",
        salary_min=450.0,
        salary_max=550.0,
        salary_period="day",
        salary_currency="GBP",
        url=f"https://example.com/jobs/{job_id}",
        source="adzuna",
        posted_at=None,
    )


def test_search_cache_key_is_stable():
    first = make_search_cache_key(
        ["AI Engineer", "Healthcare Data Engineer"],
        location=" United Kingdom ",
        pages=2,
        results_per_page=20,
    )
    second = make_search_cache_key(
        [" ai engineer ", "healthcare data engineer"],
        location="united kingdom",
        pages=2,
        results_per_page=20,
    )

    assert first == second


def test_search_cache_key_changes_when_settings_change():
    first = make_search_cache_key(
        ["AI Engineer"], "United Kingdom", 1, 20
    )
    different_location = make_search_cache_key(
        ["AI Engineer"], "London", 1, 20
    )
    different_page_size = make_search_cache_key(
        ["AI Engineer"], "United Kingdom", 1, 50
    )

    assert first != different_location
    assert first != different_page_size


def test_cache_round_trip_and_persistence(tmp_path, monkeypatch):
    monkeypatch.setattr(
        database, "DATABASE_PATH", tmp_path / "cache-test.db"
    )

    key = make_search_cache_key(["AI Engineer"])
    original_jobs = [make_job("job-1"), make_job("job-2")]

    assert get_cached_jobs(key) is None

    save_cached_jobs(key, original_jobs)

    loaded_jobs = get_cached_jobs(key)

    assert loaded_jobs is not None
    assert [job.id for job in loaded_jobs] == ["job-1", "job-2"]


def test_empty_successful_search_is_cached(tmp_path, monkeypatch):
    monkeypatch.setattr(
        database, "DATABASE_PATH", tmp_path / "cache-test.db"
    )

    key = make_search_cache_key(["Rare job title"])

    save_cached_jobs(key, [])

    result = get_cached_jobs(key)

    assert result == []
    assert result is not None


def test_expired_cache_entry_is_deleted(tmp_path, monkeypatch):
    monkeypatch.setattr(
        database, "DATABASE_PATH", tmp_path / "cache-test.db"
    )

    key = make_search_cache_key(["AI Engineer"])
    save_cached_jobs(key, [make_job()])

    expired_at = (
        datetime.now(timezone.utc) - timedelta(minutes=1)
    ).isoformat()

    with database.connect() as conn:
        conn.execute(
            """
            UPDATE search_cache
            SET expires_at = ?
            WHERE cache_key = ?
            """,
            (expired_at, key),
        )

    assert get_cached_jobs(key) is None

    with database.connect() as conn:
        row = conn.execute(
            "SELECT cache_key FROM search_cache WHERE cache_key = ?",
            (key,),
        ).fetchone()

    assert row is None


def test_clear_cache_removes_entries(tmp_path, monkeypatch):
    monkeypatch.setattr(
        database, "DATABASE_PATH", tmp_path / "cache-test.db"
    )

    save_cached_jobs(
        make_search_cache_key(["AI Engineer"]),
        [make_job()],
    )
    save_cached_jobs(
        make_search_cache_key(["Data Engineer"]),
        [],
    )

    assert get_search_cache_stats()["valid_entries"] == 2
    assert clear_search_cache() == 2
    assert get_search_cache_stats()["total_entries"] == 0

