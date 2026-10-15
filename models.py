
# models.py

"""Validated data models shared by the UI, workflow, and services."""
from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


SalaryPeriod = Literal["day", "hour", "year", "month", "week", "unknown"]


class CandidateProfile(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str = "Candidate"
    summary: str = ""
    skills: list[str] = Field(default_factory=list)
    years_experience: float | None = Field(default=None, ge=0, le=80)
    preferred_locations: list[str] = Field(default_factory=list)
    preferred_titles: list[str] = Field(default_factory=list)
    minimum_day_rate: float | None = Field(default=None, ge=0)
    employment_types: list[str] = Field(default_factory=list)


class JobPosting(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    id: str
    title: str
    company: str = "Unknown"
    description: str = ""
    location: str = "Unspecified"
    employment_type: str = "Unspecified"

    # Existing manual-job fields retained for compatibility.
    day_rate_min: float | None = Field(default=None, ge=0)
    day_rate_max: float | None = Field(default=None, ge=0)

    # General advertised compensation with explicit units.
    salary_min: float | None = Field(default=None, ge=0)
    salary_max: float | None = Field(default=None, ge=0)
    salary_period: SalaryPeriod = "unknown"
    salary_currency: str = "GBP"

    url: str = ""
    source: str = "manual"
    posted_at: str | None = None

    @model_validator(mode="after")
    def validate_compensation(self):
        if (
            self.day_rate_min is not None
            and self.day_rate_max is not None
            and self.day_rate_min > self.day_rate_max
        ):
            raise ValueError(
                "Minimum day rate cannot exceed maximum day rate."
            )

        if (
            self.salary_min is not None
            and self.salary_max is not None
            and self.salary_min > self.salary_max
        ):
            raise ValueError(
                "Minimum salary cannot exceed maximum salary."
            )

        self.salary_currency = self.salary_currency.upper()

        if (
            len(self.salary_currency) != 3
            or not self.salary_currency.isalpha()
        ):
            raise ValueError(
                "Salary currency must be a three-letter code."
            )

        return self


class MatchResult(BaseModel):
    job: JobPosting
    score: float = Field(ge=0, le=100)
    matched_skills: list[str] = Field(default_factory=list)
    missing_skills: list[str] = Field(default_factory=list)
    rationale: list[str] = Field(default_factory=list)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
