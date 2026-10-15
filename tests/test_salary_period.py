
# tests/test_salary_period.py

from providers.adzuna import _salary_period


def test_detects_daily_rate():
    assert _salary_period("Contractor paid £500 per day") == "day"


def test_detects_annual_salary():
    assert (
        _salary_period("Annual salary £60,000 per annum")
        == "year"
    )


def test_unknown_period_is_not_guessed():
    assert (
        _salary_period("Competitive salary £60,000")
        == "unknown"
    )


def test_ambiguous_period_is_unknown():
    assert (
        _salary_period(
            "£500 per day, with annual salary review"
        )
        == "unknown"
    )
