
# Filename: config.py
# Full path: C:\Technative\ai-jobmatch-agent\config.py

"""Environment-backed application configuration."""

import os
from pathlib import Path

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parent

load_dotenv(PROJECT_ROOT / ".env")


def _int_env(
    name: str,
    default: int,
    minimum: int,
    maximum: int,
) -> int:
    """Read an integer environment variable within safe bounds."""
    try:
        value = int(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        value = default

    return max(minimum, min(value, maximum))


DATABASE_PATH = Path(
    os.getenv("DATABASE_PATH", "data/jobmatch.db")
)

if not DATABASE_PATH.is_absolute():
    DATABASE_PATH = PROJECT_ROOT / DATABASE_PATH

MAX_UPLOAD_MB = _int_env(
    "MAX_UPLOAD_MB",
    10,
    1,
    50,
)

ADZUNA_APP_ID = os.getenv(
    "ADZUNA_APP_ID",
    "",
).strip()

ADZUNA_APP_KEY = os.getenv(
    "ADZUNA_APP_KEY",
    "",
).strip()

ADZUNA_COUNTRY = (
    os.getenv("ADZUNA_COUNTRY", "gb").strip().lower()
    or "gb"
)

# Ollama connection settings.
# Inside Docker, the hostname "ollama" resolves to the Ollama container.
OLLAMA_BASE_URL = (
    os.getenv(
        "OLLAMA_BASE_URL",
        "http://localhost:11434",
    ).strip().rstrip("/")
    or "http://localhost:11434"
)

OLLAMA_MODEL = (
    os.getenv("OLLAMA_MODEL", "qwen3:8b").strip()
    or "qwen3:8b"
)

OLLAMA_TIMEOUT_SECONDS = _int_env(
    "OLLAMA_TIMEOUT_SECONDS",
    300,
    5,
    600,
)
