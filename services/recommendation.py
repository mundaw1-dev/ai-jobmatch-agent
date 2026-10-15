
# File: services/recommendation.py
"""Recommendation summaries built from deterministic match evidence."""

from models import MatchResult


def recommendation_for(result: MatchResult) -> str:
    """Create a concise, evidence-based recommendation."""
    if result.score >= 75:
        level = "Strong match"
    elif result.score >= 50:
        level = "Potential match"
    else:
        level = "Stretch match"

    skills = (
        ", ".join(result.matched_skills[:6])
        if result.matched_skills
        else "no listed profile skills detected in the advert"
    )

    evidence = " ".join(result.rationale[:4])

    return (
        f"{level} ({result.score:.1f}/100; heuristic score, not a probability). "
        f"Relevant skills: {skills}. {evidence} "
        "Check the full advert and confirm essential requirements before applying."
    )
