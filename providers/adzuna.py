
# providers/adzuna.py

"""Adzuna API client with bounded multi-query search and explicit salary units."""

import hashlib
import math
import re
from urllib.parse import urlsplit, urlunsplit

import requests

from config import ADZUNA_APP_ID, ADZUNA_APP_KEY, ADZUNA_COUNTRY
from models import JobPosting


def _salary_period(text: str) -> str:
    """Infer a salary period only when wording identifies one unambiguously."""
    text = text.casefold()

    patterns = [
        (r"\b(?:per day|a day|daily|/\s*day|day rate)\b", "day"),
        (r"\b(?:per hour|an hour|hourly|/\s*hour)\b", "hour"),
        (r"\b(?:per month|a month|monthly|/\s*month)\b", "month"),
        (r"\b(?:per week|a week|weekly|/\s*week)\b", "week"),
        (
            r"\b(?:per year|a year|annually|annual salary|per annum|p\.?a\.?)\b",
            "year",
        ),
    ]

    matches = {
        period
        for pattern, period in patterns
        if re.search(pattern, text)
    }
    return matches.pop() if len(matches) == 1 else "unknown"


def _normalise_url(url: str) -> str:
    """Remove query strings and fragments for URL-based deduplication."""
    try:
        parts = urlsplit(url.strip())
        if not parts.scheme or not parts.netloc:
            return ""
        return urlunsplit(
            (parts.scheme.casefold(), parts.netloc.casefold(), parts.path.rstrip("/"), "", "")
        )
    except (TypeError, ValueError):
        return ""


def _job_identity(job: JobPosting) -> str:
    """Return a stable deduplication key for a job."""
    if job.id:
        return "id:" + job.id.casefold()

    normalised_url = _normalise_url(job.url or "")
    if normalised_url:
        return "url:" + normalised_url

    fallback = "|".join(
        (
            (job.title or "").strip().casefold(),
            (job.company or "").strip().casefold(),
            (job.location or "").strip().casefold(),
        )
    )
    return "fallback:" + hashlib.sha256(fallback.encode("utf-8")).hexdigest()


class AdzunaClient:
    BASE_URL = "https://api.adzuna.com/v1/api/jobs"
    MAX_QUERIES = 8
    MAX_PAGES = 3
    MAX_RESULTS_PER_PAGE = 50

    def __init__(
        self,
        app_id: str = ADZUNA_APP_ID,
        app_key: str = ADZUNA_APP_KEY,
        country: str = ADZUNA_COUNTRY,
        timeout: int = 12,
    ):
        self.app_id = app_id
        self.app_key = app_key
        self.country = country
        self.timeout = max(1, min(int(timeout), 60))

    @property
    def configured(self) -> bool:
        return bool(
            isinstance(self.app_id, str)
            and self.app_id.strip()
            and isinstance(self.app_key, str)
            and self.app_key.strip()
        )

    def search(
        self,
        query: str,
        location: str = "",
        page: int = 1,
        results_per_page: int = 20,
    ) -> list[JobPosting]:
        """Search one query and one page."""
        if not self.configured:
            raise RuntimeError(
                "Adzuna is not configured. Add ADZUNA_APP_ID and "
                "ADZUNA_APP_KEY to .env."
            )

        if not isinstance(query, str) or not query.strip():
            raise ValueError("A search query is required.")

        page = max(1, min(int(page), 50))
        results_per_page = max(1, min(int(results_per_page), self.MAX_RESULTS_PER_PAGE))

        params = {
            "app_id": self.app_id,
            "app_key": self.app_key,
            "results_per_page": results_per_page,
            "what": query.strip()[:150],
        }

        if isinstance(location, str) and location.strip():
            params["where"] = location.strip()[:150]

        response = requests.get(
            f"{self.BASE_URL}/{self.country}/search/{page}",
            params=params,
            timeout=self.timeout,
        )
        response.raise_for_status()

        try:
            payload = response.json()
        except (ValueError, requests.exceptions.JSONDecodeError) as exc:
            raise ValueError("Adzuna returned invalid JSON.") from exc

        if not isinstance(payload, dict):
            raise ValueError("Adzuna returned an invalid response.")

        results = payload.get("results", [])
        if not isinstance(results, list):
            raise ValueError("Adzuna returned an invalid results collection.")

        jobs = []

        for item in results:
            if not isinstance(item, dict):
                continue

            title = str(item.get("title") or "Untitled")[:250]
            description = str(item.get("description") or "")[:20_000]

            company_data = item.get("company")
            location_data = item.get("location")

            company = (
                str(company_data.get("display_name") or "Unknown")[:200]
                if isinstance(company_data, dict)
                else "Unknown"
            )
            location_name = (
                str(location_data.get("display_name") or "Unspecified")[:250]
                if isinstance(location_data, dict)
                else "Unspecified"
            )

            url = str(item.get("redirect_url") or "")[:2000]
            source_id = str(item.get("id") or url or title + company)
            stable_id = hashlib.sha256(source_id.encode("utf-8")).hexdigest()[:24]

            salary_min, salary_max = self._parse_salary(
                item.get("salary_min"),
                item.get("salary_max"),
            )
            period = _salary_period(" ".join((title, description)))

            contract_type = str(
                item.get("contract_type")
                or item.get("contract_time")
                or "Unspecified"
            )[:100]

            jobs.append(
                JobPosting(
                    id="adzuna-" + stable_id,
                    title=title,
                    company=company,
                    description=description,
                    location=location_name,
                    employment_type=contract_type,
                    salary_min=salary_min,
                    salary_max=salary_max,
                    salary_period=period,
                    salary_currency="GBP",
                    url=url,
                    source="adzuna",
                    posted_at=(
                        str(item["created"])
                        if item.get("created") is not None
                        else None
                    ),
                )
            )

        return jobs

    def search_many(
        self,
        queries: list[str],
        location: str = "",
        pages: int = 1,
        results_per_page: int = 20,
    ) -> tuple[list[JobPosting], list[str]]:
        """
        Search multiple queries and pages.

        Returns (unique_jobs, errors). A failed query or page does not discard
        successful results. Error messages never include request URLs or keys.
        """
        if not self.configured:
            raise RuntimeError(
                "Adzuna is not configured. Add ADZUNA_APP_ID and "
                "ADZUNA_APP_KEY to .env."
            )

        if not isinstance(queries, list):
            raise ValueError("Queries must be supplied as a list.")

        unique_queries = []
        seen_queries = set()

        for query in queries:
            if not isinstance(query, str) or not query.strip():
                continue

            cleaned = query.strip()[:150]
            key = cleaned.casefold()

            if key not in seen_queries:
                seen_queries.add(key)
                unique_queries.append(cleaned)

        if not unique_queries:
            raise ValueError("Enter at least one non-empty search query.")

        if len(unique_queries) > self.MAX_QUERIES:
            raise ValueError(
                f"Use no more than {self.MAX_QUERIES} unique search queries."
            )

        pages = max(1, min(int(pages), self.MAX_PAGES))
        results_per_page = max(
            1, min(int(results_per_page), self.MAX_RESULTS_PER_PAGE)
        )

        jobs_by_identity: dict[str, JobPosting] = {}
        errors: list[str] = []

        for query in unique_queries:
            for page in range(1, pages + 1):
                try:
                    page_jobs = self.search(
                        query=query,
                        location=location,
                        page=page,
                        results_per_page=results_per_page,
                    )
                except requests.HTTPError as exc:
                    status = (
                        exc.response.status_code
                        if exc.response is not None
                        else "unknown"
                    )
                    errors.append(
                        f"'{query}', page {page}: HTTP error {status}."
                    )
                    break
                except requests.Timeout:
                    errors.append(f"'{query}', page {page}: request timed out.")
                    break
                except requests.RequestException:
                    errors.append(f"'{query}', page {page}: network request failed.")
                    break
                except (ValueError, RuntimeError):
                    errors.append(
                        f"'{query}', page {page}: response or configuration error."
                    )
                    break

                for job in page_jobs:
                    identity = _job_identity(job)
                    if identity not in jobs_by_identity:
                        jobs_by_identity[identity] = job

                # An empty page means there are no more results for this query.
                if not page_jobs:
                    break

        return list(jobs_by_identity.values()), errors

    @staticmethod
    def _parse_salary(
        raw_min,
        raw_max,
    ) -> tuple[float | None, float | None]:
        """Reject invalid salary ranges without inventing compensation."""
        try:
            salary_min = float(raw_min) if raw_min is not None else None
            salary_max = float(raw_max) if raw_max is not None else None
        except (TypeError, ValueError, OverflowError):
            return None, None

        values = [
            value for value in (salary_min, salary_max) if value is not None
        ]

        if any(not math.isfinite(value) or value < 0 for value in values):
            return None, None

        if (
            salary_min is not None
            and salary_max is not None
            and salary_min > salary_max
        ):
            return None, None

        return salary_min, salary_max
