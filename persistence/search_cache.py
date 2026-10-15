
# persistence/search_cache.py

"""Persistent SQLite cache for Adzuna job-search results."""

import hashlib
import json
from datetime import datetime, timedelta, timezone
from typing import Any

from database import connect, initialize_database
from models import JobPosting


DEFAULT_TTL_HOURS = 24


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def make_search_cache_key(
    queries: list[str],
    location: str = "",
    pages: int = 1,
    results_per_page: int = 20,
) -> str:
    """Build a stable key from the effective search settings."""
    if not isinstance(queries, list):
        raise ValueError("queries must be a list")

    normalised_queries = []
    seen = set()

    for query in queries:
        if not isinstance(query, str):
            continue

        cleaned = " ".join(query.split())
        identity = cleaned.casefold()

        if cleaned and identity not in seen:
            seen.add(identity)
            normalised_queries.append(identity)

    if not normalised_queries:
        raise ValueError("At least one non-empty query is required")

    payload = {
        "queries": normalised_queries,
        "location": " ".join(location.split()).casefold(),
        "pages": int(pages),
        "results_per_page": int(results_per_page),
    }

    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")

    return hashlib.sha256(encoded).hexdigest()


def get_cached_jobs(
    cache_key: str,
    ttl_hours: int = DEFAULT_TTL_HOURS,
) -> list[JobPosting] | None:
    """
    Return cached jobs when the entry is still valid.

    None means a cache miss. An empty list means a valid cached
    search that returned zero jobs.
    """
    if ttl_hours < 1:
        raise ValueError("ttl_hours must be at least 1")

    initialize_database()
    now = _utc_now()

    with connect() as conn:
        row = conn.execute(
            """
            SELECT results_json, cached_at, expires_at
            FROM search_cache
            WHERE cache_key = ?
            """,
            (cache_key,),
        ).fetchone()

        if row is None:
            return None

        try:
            expires_at = datetime.fromisoformat(row["expires_at"])
            if expires_at <= now:
                conn.execute(
                    "DELETE FROM search_cache WHERE cache_key = ?",
                    (cache_key,),
                )
                return None

            raw_jobs = json.loads(row["results_json"])
            if not isinstance(raw_jobs, list):
                raise ValueError("Cached result is not a list")

            return [
                JobPosting.model_validate(item)
                for item in raw_jobs
            ]

        except (ValueError, TypeError, json.JSONDecodeError):
            conn.execute(
                "DELETE FROM search_cache WHERE cache_key = ?",
                (cache_key,),
            )
            return None


def save_cached_jobs(
    cache_key: str,
    jobs: list[JobPosting],
    ttl_hours: int = DEFAULT_TTL_HOURS,
) -> None:
    """Save a successful search, including a search with zero matches."""
    if ttl_hours < 1:
        raise ValueError("ttl_hours must be at least 1")

    initialize_database()

    now = _utc_now()
    expires_at = now + timedelta(hours=ttl_hours)

    results_json = json.dumps(
        [job.model_dump(mode="json") for job in jobs],
        ensure_ascii=False,
    )

    with connect() as conn:
        conn.execute(
            """
            INSERT INTO search_cache (
                cache_key, results_json, cached_at, expires_at
            )
            VALUES (?, ?, ?, ?)
            ON CONFLICT(cache_key) DO UPDATE SET
                results_json = excluded.results_json,
                cached_at = excluded.cached_at,
                expires_at = excluded.expires_at
            """,
            (
                cache_key,
                results_json,
                now.isoformat(),
                expires_at.isoformat(),
            ),
        )


def clear_search_cache() -> int:
    """Delete all cached searches and return the number removed."""
    initialize_database()

    with connect() as conn:
        cursor = conn.execute("DELETE FROM search_cache")
        return cursor.rowcount


def get_search_cache_stats() -> dict[str, Any]:
    """Return basic cache statistics for diagnostics and the UI."""
    initialize_database()
    now = _utc_now().isoformat()

    with connect() as conn:
        row = conn.execute(
            """
            SELECT
                COUNT(*) AS total,
                SUM(CASE WHEN expires_at > ? THEN 1 ELSE 0 END) AS valid
            FROM search_cache
            """,
            (now,),
        ).fetchone()

    return {
        "total_entries": row["total"] or 0,
        "valid_entries": row["valid"] or 0,
    }

