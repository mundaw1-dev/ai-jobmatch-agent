
# File: services/matcher.py
"""Deterministic, explainable multi-criteria job matching."""

import re

from models import CandidateProfile, JobPosting, MatchResult
from services.candidate_profile import SKILL_ALIASES as PROFILE_SKILL_ALIASES


# Each group contains phrases describing the same skill.
_BASE_ALIAS_GROUPS = [
    {"llm", "large language model", "large language models", "llms"},
    {"postgresql", "postgres"},
    {"rest api", "rest apis"},
    {"rag", "retrieval augmented generation"},
    {"sql server", "microsoft sql server", "mssql", "sqlserver"},
    {"t-sql", "tsql", "transact-sql", "transact sql"},
    {"snowflake cortex", "cortex ai"},
    {"vector search", "semantic search", "similarity search"},
    {"etl", "extract transform load"},
    {"elt", "extract load transform"},
    {"lora", "low-rank adaptation"},
    {
        "qlora",
        "quantized low-rank adaptation",
        "quantised low-rank adaptation",
    },
    {"nlp", "natural language processing"},
    {"llama.cpp", "llama cpp", "llama-cpp"},
    {"chromadb", "chroma"},
]

SENIORITY_WORDS = {
    "junior",
    "associate",
    "senior",
    "lead",
    "principal",
    "staff",
    "graduate",
    "mid",
}

HEALTHCARE_TERMS = {
    "healthcare",
    "health care",
    "clinical",
    "life sciences",
    "life science",
    "pharma",
    "pharmaceutical",
    "pharmaceuticals",
    "omop",
    "cprd",
    "pharmetrics",
    "lprx",
    "medical data",
    "patient data",
    "electronic health record",
    "electronic health records",
    "ehr",
    "claims data",
    "clinical research",
}

EMPLOYMENT_ALIASES = {
    "permanent": {
        "permanent",
        "full time",
        "full-time",
        "employee",
        "employed",
    },
    "contract": {
        "contract",
        "contractor",
        "freelance",
        "freelancer",
        "outside ir35",
        "inside ir35",
        "fixed term",
        "fixed-term",
        "temporary",
    },
}


def _normalise(value: str) -> str:
    """Normalise text while retaining common technology punctuation."""
    value = value.casefold()
    value = re.sub(r"\bt[\s-]*sql\b", "tsql", value)
    value = re.sub(r"[^a-z0-9+#]+", " ", value)
    return " ".join(value.split())


def _contains_phrase(text: str, phrase: str) -> bool:
    """Match a complete phrase, not a substring inside another word."""
    text_norm = f" {_normalise(text)} "
    phrase_norm = _normalise(phrase)
    return bool(phrase_norm) and f" {phrase_norm} " in text_norm


def _alias_groups() -> list[set[str]]:
    """Combine built-in aliases with aliases from the candidate profile."""
    groups = [set(group) for group in _BASE_ALIAS_GROUPS]

    for canonical, variants in PROFILE_SKILL_ALIASES.items():
        groups.append({canonical, *variants})

    return [
        {_normalise(item) for item in group if _normalise(item)}
        for group in groups
    ]


_ALIAS_GROUPS = _alias_groups()


def _skill_variants(skill: str) -> set[str]:
    """Return all known textual forms of a skill."""
    normalised = _normalise(skill)

    for group in _ALIAS_GROUPS:
        if normalised in group:
            return group

    return {normalised} if normalised else set()


def _canonical_skill(skill: str) -> str:
    """Map skill aliases to one stable value for scoring."""
    normalised = _normalise(skill)

    for group in _ALIAS_GROUPS:
        if normalised in group:
            return sorted(group)[0]

    return normalised


def _skill_found(advert: str, skill: str) -> bool:
    return any(
        _contains_phrase(advert, variant)
        for variant in _skill_variants(skill)
    )


def _title_key(title: str) -> str:
    words = _normalise(title).split()
    return " ".join(
        word for word in words if word not in SENIORITY_WORDS
    )


def _title_matches(job_title: str, preferred_title: str) -> bool:
    job_key = _title_key(job_title)
    preferred_key = _title_key(preferred_title)

    if not job_key or not preferred_key:
        return False

    return (
        job_key == preferred_key
        or _contains_phrase(job_key, preferred_key)
        or _contains_phrase(preferred_key, job_key)
    )


def _location_matches(job_location: str, preferred_location: str) -> bool:
    job = _normalise(job_location)
    preferred = _normalise(preferred_location)

    if not job or not preferred:
        return False

    if preferred == "remote":
        return (
            "remote" in job.split()
            or "homebased" in job.split()
            or "work from home" in job
        )

    return _contains_phrase(job, preferred)


def _employment_category(value: str) -> str | None:
    """Classify common job employment labels."""
    normalised = _normalise(value)

    for category, aliases in EMPLOYMENT_ALIASES.items():
        if any(
            _contains_phrase(normalised, alias)
            for alias in aliases
        ):
            return category

    return None


def _employment_matches(
    job_type: str,
    preferred_types: list[str],
) -> bool:
    job_category = _employment_category(job_type)

    if job_category is None:
        return False

    return any(
        _employment_category(preference) == job_category
        for preference in preferred_types
    )


def _healthcare_signal(text: str) -> bool:
    return any(
        _contains_phrase(text, term)
        for term in HEALTHCARE_TERMS
    )


def _rate_assessment(
    profile: CandidateProfile,
    job: JobPosting,
) -> tuple[float, str]:
    """Score comparable compensation without inventing a day rate."""
    if profile.minimum_day_rate is None:
        return (
            5.0,
            "No minimum day-rate preference specified; neutral points applied.",
        )

    target = profile.minimum_day_rate
    currency = (job.salary_currency or "").upper()

    if currency != "GBP":
        return (
            5.0,
            "Rate uncertain: missing or below the minimum cannot be "
            f"confirmed because the advert currency is {currency or 'unknown'}, "
            "not GBP.",
        )

    # Preserve manually entered day-rate fields.
    minimum = job.day_rate_min
    maximum = job.day_rate_max

    # Salary fields are comparable only when explicitly labelled daily.
    if job.salary_period == "day":
        if minimum is None:
            minimum = job.salary_min
        if maximum is None:
            maximum = job.salary_max

    if minimum is None and maximum is None:
        return (
            5.0,
            "Rate unknown: missing or below the minimum cannot be "
            "confirmed because no comparable GBP day rate was supplied.",
        )

    if minimum is not None and minimum >= target:
        return (
            10.0,
            f"Advertised minimum day rate meets the minimum "
            f"(£{minimum:,.2f} against the £{target:,.2f} target).",
        )

    if maximum is not None and maximum < target:
        return (
            0.0,
            f"Advertised maximum day rate is below the minimum "
            f"(£{maximum:,.2f} maximum against the £{target:,.2f} target).",
        )

    return (
        5.0,
        f"Rate uncertain: the advertised range does not confirm "
        f"that the minimum meets the £{target:,.2f} per-day target.",
    )


def match_job(
    profile: CandidateProfile,
    job: JobPosting,
) -> MatchResult:
    """Score one job and return the evidence behind the score."""
    skills = list(
        dict.fromkeys(
            skill.strip()
            for skill in profile.skills
            if skill.strip()
        )
    )

    advert = f"{job.title} {job.description}"

    canonical_skills = {
        _canonical_skill(skill)
        for skill in skills
        if _canonical_skill(skill)
    }

    matched_canonical = {
        _canonical_skill(skill)
        for skill in skills
        if _skill_found(advert, skill)
    }

    matched = sorted(
        skill for skill in skills
        if _skill_found(advert, skill)
    )

    missing = sorted(
        skill for skill in skills
        if not _skill_found(advert, skill)
    )

    skill_score = (
        55.0 * len(matched_canonical) / max(1, len(canonical_skills))
    )

    rationale = [
        f"Skill overlap: {len(matched_canonical)} of "
        f"{len(canonical_skills)} distinct profile skills found."
    ]

    # Preferred title: one valid title match earns the full criterion.
    if profile.preferred_titles:
        title_hits = [
            title for title in profile.preferred_titles
            if _title_matches(job.title, title)
        ]
        title_score = 15.0 if title_hits else 0.0
        rationale.append(
            f"Preferred title matched: {title_hits[0]}."
            if title_hits
            else "No preferred job title matched."
        )
    else:
        title_score = 7.5
        rationale.append(
            "No preferred titles configured; neutral points applied."
        )

    # Remote preference is checked against both location and advert text.
    if profile.preferred_locations:
        location_hits = [
            location for location in profile.preferred_locations
            if _location_matches(
                (
                    f"{job.location} {job.description}"
                    if _normalise(location) == "remote"
                    else job.location
                ),
                location,
            )
        ]
        location_score = 10.0 if location_hits else 0.0
        rationale.append(
            "Location preference matched: " + ", ".join(location_hits) + "."
            if location_hits
            else "No preferred location matched."
        )
    else:
        location_score = 5.0
        rationale.append(
            "No location preferences configured; neutral points applied."
        )

    # A missing preference is neutral, not a penalty.
    if profile.employment_types:
        employment_match = _employment_matches(
            job.employment_type or "",
            profile.employment_types,
        )
        employment_score = 5.0 if employment_match else 0.0
        rationale.append(
            f"Preferred employment type matched: {job.employment_type}."
            if employment_match
            else (
                "Advertised employment type does not match a configured "
                f"preference ({job.employment_type or 'unknown'})."
            )
        )
    else:
        employment_score = 5.0
        rationale.append(
            "No employment-type preferences configured; neutral points applied."
        )

    # Healthcare relevance is based on the advert and candidate profile.
    profile_text = " ".join(profile.skills) + " " + profile.summary
    profile_is_healthcare_focused = _healthcare_signal(profile_text)
    advert_is_healthcare_focused = _healthcare_signal(advert)

    if advert_is_healthcare_focused:
        healthcare_score = 5.0
        rationale.append(
            "Healthcare/life-sciences relevance detected in the advert."
        )
    elif profile_is_healthcare_focused:
        healthcare_score = 0.0
        rationale.append(
            "Healthcare/life-sciences relevance not detected in the advert."
        )
    else:
        healthcare_score = 2.5
        rationale.append(
            "Healthcare relevance not scored: no healthcare specialism "
            "detected in the profile or advert."
        )

    rate_score, rate_reason = _rate_assessment(profile, job)
    rationale.append(rate_reason)

    score = round(
        min(
            100.0,
            max(
                0.0,
                skill_score
                + title_score
                + location_score
                + employment_score
                + healthcare_score
                + rate_score,
            ),
        ),
        1,
    )

    return MatchResult(
        job=job,
        score=score,
        matched_skills=matched,
        missing_skills=missing,
        rationale=rationale,
    )


def rank_jobs(
    profile: CandidateProfile,
    jobs: list[JobPosting],
) -> list[MatchResult]:
    """Rank jobs by score, with deterministic tie-breaking."""
    return sorted(
        (match_job(profile, job) for job in jobs),
        key=lambda result: (
            -result.score,
            result.job.title.casefold(),
            result.job.id,
        ),
    )
