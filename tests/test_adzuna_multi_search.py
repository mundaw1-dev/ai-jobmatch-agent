# tests/test_adzuna_multi_search.py

"""Tests for multi-query Adzuna search, pagination and failure handling."""

import requests
import pytest

from models import JobPosting
from providers.adzuna import AdzunaClient


def make_job(
    job_id: str,
    title: str = "AI Engineer",
    url: str | None = None,
) -> JobPosting:
    """Create a valid job fixture without making network requests."""
    return JobPosting(
        id=job_id,
        title=title,
        company="Example Ltd",
        description="Python, SQL and healthcare AI engineering.",
        location="Remote, United Kingdom",
        employment_type="Contract",
        salary_min=450.0,
        salary_max=550.0,
        salary_period="day",
        salary_currency="GBP",
        url=url or f"https://example.com/jobs/{job_id}",
        source="adzuna",
        posted_at=None,
    )


def make_client() -> AdzunaClient:
    """Return a configured client that can be tested offline."""
    return AdzunaClient(
        app_id="test-app-id",
        app_key="test-app-key",
        country="gb",
        timeout=2,
    )


def test_search_many_rejects_empty_queries():
    client = make_client()

    with pytest.raises(ValueError, match="at least one"):
        client.search_many(["", "   "])


def test_search_many_rejects_too_many_unique_queries():
    client = make_client()
    queries = [f"AI role {number}" for number in range(9)]

    with pytest.raises(ValueError, match="no more than"):
        client.search_many(queries)


def test_search_many_removes_duplicate_queries_and_jobs(monkeypatch):
    client = make_client()
    first_job = make_job("job-1")
    second_job = make_job("job-2", title="Healthcare AI Engineer")
    calls = []

    def fake_search(
        query,
        location="",
        page=1,
        results_per_page=20,
    ):
        calls.append((query, page, location, results_per_page))

        if query == "AI Engineer" and page == 1:
            return [first_job]

        if query == "Healthcare AI Engineer" and page == 1:
            # job-1 appears in both searches.
            return [first_job, second_job]

        return []

    monkeypatch.setattr(client, "search", fake_search)

    jobs, errors = client.search_many(
        queries=[
            "AI Engineer",
            " ai engineer ",
            "Healthcare AI Engineer",
        ],
        location="Remote",
        pages=1,
        results_per_page=10,
    )

    assert [job.id for job in jobs] == ["job-1", "job-2"]
    assert errors == []
    assert len(calls) == 2
    assert calls[0] == ("AI Engineer", 1, "Remote", 10)
    assert calls[1] == (
        "Healthcare AI Engineer",
        1,
        "Remote",
        10,
    )


def test_search_many_fetches_multiple_pages(monkeypatch):
    client = make_client()
    first_job = make_job("job-1")
    second_job = make_job("job-2")
    calls = []

    def fake_search(query, location="", page=1, results_per_page=20):
        calls.append(page)

        if page == 1:
            return [first_job]

        if page == 2:
            return [second_job]

        return []

    monkeypatch.setattr(client, "search", fake_search)

    jobs, errors = client.search_many(
        queries=["AI Engineer"],
        pages=2,
    )

    assert [job.id for job in jobs] == ["job-1", "job-2"]
    assert calls == [1, 2]
    assert errors == []


def test_search_many_stops_pagination_on_empty_page(monkeypatch):
    client = make_client()
    calls = []

    def fake_search(query, location="", page=1, results_per_page=20):
        calls.append(page)

        if page == 1:
            return [make_job("job-1")]

        return []

    monkeypatch.setattr(client, "search", fake_search)

    jobs, errors = client.search_many(
        queries=["AI Engineer"],
        pages=3,
    )

    assert len(jobs) == 1
    assert calls == [1, 2]
    assert errors == []


def test_search_many_preserves_successful_results_after_timeout(
    monkeypatch,
):
    client = make_client()
    successful_job = make_job("job-1")

    def fake_search(query, location="", page=1, results_per_page=20):
        if query == "Healthcare AI Engineer":
            raise requests.Timeout("Simulated timeout")

        return [successful_job]

    monkeypatch.setattr(client, "search", fake_search)

    jobs, errors = client.search_many(
        queries=["AI Engineer", "Healthcare AI Engineer"],
    )

    assert [job.id for job in jobs] == ["job-1"]
    assert len(errors) == 1
    assert "timed out" in errors[0]
    assert "AI Engineer" not in errors[0] or "Healthcare AI Engineer" in errors[0]


def test_search_many_reports_http_status_without_request_details(
    monkeypatch,
):
    client = make_client()

    def fake_search(query, location="", page=1, results_per_page=20):
        raise requests.HTTPError(
            "Request failed with app_key=secret-test-key"
        )

    monkeypatch.setattr(client, "search", fake_search)

    jobs, errors = client.search_many(
        queries=["AI Engineer"],
    )

    assert jobs == []
    assert len(errors) == 1
    assert "HTTP error" in errors[0]
    assert "secret-test-key" not in errors[0]
    assert "test-app-key" not in errors[0]


def test_search_many_requires_credentials():
    client = AdzunaClient(
        app_id="",
        app_key="",
        country="gb",
    )

    with pytest.raises(RuntimeError, match="not configured"):
        client.search_many(["AI Engineer"])


def test_search_many_rejects_non_list_queries():
    client = make_client()

    with pytest.raises(ValueError, match="list"):
        client.search_many("AI Engineer")