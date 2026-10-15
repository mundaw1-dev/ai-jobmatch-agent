
# persistence/repositories.py
"""SQLite repositories for profiles, jobs, and shortlist."""

from datetime import datetime, timezone

from database import connect
from models import CandidateProfile, JobPosting


def _now() -> str:
    """Return the current UTC time as an ISO 8601 string."""
    return datetime.now(timezone.utc).isoformat()


def save_profile(profile: CandidateProfile) -> None:
    """Insert or update the single stored candidate profile."""
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO profiles (id, profile_json, updated_at)
            VALUES (1, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                profile_json = excluded.profile_json,
                updated_at = excluded.updated_at
            """,
            (profile.model_dump_json(), _now()),
        )


def load_profile() -> CandidateProfile | None:
    """Load the stored candidate profile, if one exists."""
    with connect() as conn:
        row = conn.execute(
            "SELECT profile_json FROM profiles WHERE id = 1"
        ).fetchone()

    if row is None:
        return None

    return CandidateProfile.model_validate_json(row["profile_json"])


def save_jobs(jobs: list[JobPosting]) -> None:
    """Insert or update jobs without deleting existing records."""
    if not jobs:
        return

    saved_at = _now()

    with connect() as conn:
        conn.executemany(
            """
            INSERT INTO jobs (id, job_json, source, saved_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                job_json = excluded.job_json,
                source = excluded.source,
                saved_at = excluded.saved_at
            """,
            [
                (
                    job.id,
                    job.model_dump_json(),
                    job.source,
                    saved_at,
                )
                for job in jobs
            ],
        )


def load_jobs() -> list[JobPosting]:
    """Load all stored jobs, newest saved first."""
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT job_json
            FROM jobs
            ORDER BY saved_at DESC
            """
        ).fetchall()

    return [
        JobPosting.model_validate_json(row["job_json"])
        for row in rows
    ]


def add_to_shortlist(
    job: JobPosting,
    notes: str = "",
) -> None:
    """
    Save a job and add it to the shortlist.

    If the job is already shortlisted, preserve its existing notes
    and saved timestamp. Use update_shortlist_notes() to change notes.
    """
    save_jobs([job])

    with connect() as conn:
        conn.execute(
            """
            INSERT INTO shortlist (job_id, notes, saved_at)
            VALUES (?, ?, ?)
            ON CONFLICT(job_id) DO NOTHING
            """,
            (job.id, notes[:2000], _now()),
        )


def load_shortlist() -> list[tuple[JobPosting, str]]:
    """Return shortlisted jobs with their notes, newest first."""
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT jobs.job_json, shortlist.notes
            FROM shortlist
            JOIN jobs ON jobs.id = shortlist.job_id
            ORDER BY shortlist.saved_at DESC
            """
        ).fetchall()

    return [
        (
            JobPosting.model_validate_json(row["job_json"]),
            row["notes"],
        )
        for row in rows
    ]


def update_shortlist_notes(
    job_id: str,
    notes: str,
) -> bool:
    """Update notes for a shortlisted job; return whether it existed."""
    with connect() as conn:
        cursor = conn.execute(
            """
            UPDATE shortlist
            SET notes = ?
            WHERE job_id = ?
            """,
            (notes[:2000], job_id),
        )

    return cursor.rowcount > 0


def remove_from_shortlist(job_id: str) -> None:
    """Remove a job from the shortlist without deleting the job itself."""
    with connect() as conn:
        conn.execute(
            "DELETE FROM shortlist WHERE job_id = ?",
            (job_id,),
        )
