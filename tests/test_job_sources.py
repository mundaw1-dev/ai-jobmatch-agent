import pytest
from providers.adzuna import AdzunaClient

def test_adzuna_requires_credentials():
    with pytest.raises(RuntimeError): AdzunaClient(app_id="", app_key="").search("AI Engineer")

def test_adzuna_requires_query():
    with pytest.raises(ValueError): AdzunaClient(app_id="x", app_key="y").search(" ")
