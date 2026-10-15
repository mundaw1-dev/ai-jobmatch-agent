
# File: services/candidate_profile.py
"""Structured candidate profile defaults for Will Munda."""

from models import CandidateProfile


SKILL_ALIASES: dict[str, list[str]] = {
    "LLM": [
        "large language model",
        "large language models",
        "llms",
    ],
    "RAG": [
        "retrieval augmented generation",
        "retrieval-augmented generation",
    ],
    "SQL Server": [
        "microsoft sql server",
        "mssql",
        "sqlserver",
    ],
    "T-SQL": [
        "transact-sql",
        "transact sql",
        "tsql",
    ],
    "Snowflake": [
        "snowflake cortex",
        "cortex ai",
        "cortex analyst",
    ],
    "Vector search": [
        "vector database",
        "semantic search",
        "similarity search",
    ],
    "ETL": [
        "extract transform load",
        "data pipelines",
    ],
    "ELT": [
        "extract load transform",
    ],
    "LoRA": [
        "low-rank adaptation",
    ],
    "QLoRA": [
        "quantized low-rank adaptation",
        "quantised low-rank adaptation",
    ],
    "NLP": [
        "natural language processing",
    ],
    "llama.cpp": [
        "llama cpp",
        "llama-cpp",
    ],
    "ChromaDB": [
        "chromadb",
        "chroma",
    ],
    "FAISS": [
        "facebook ai similarity search",
    ],
}

PREFERRED_TITLES = [
    "Senior AI Engineer",
    "Senior AI and Data Engineer",
    "Senior Data Engineer",
    "Forward-Deployed Engineer",
    "Forward Deployed AI Engineer",
    "AI Platform Engineer",
    "Healthcare AI Engineer",
    "Healthcare Data Engineer",
]

PREFERRED_LOCATIONS = [
    "Remote",
    "United Kingdom",
    "Brighton",
]

PREFERRED_SKILLS = [
    "Python",
    "SQL",
    "T-SQL",
    "SQL Server",
    "Snowflake",
    "Snowflake Cortex",
    "ETL",
    "ELT",
    "Healthcare data",
    "Life sciences",
    "Clinical data",
    "OMOP",
    "CPRD",
    "Pharmetrics",
    "LPRx",
    "LLM",
    "RAG",
    "LangChain",
    "LlamaIndex",
    "Ollama",
    "llama.cpp",
    "Hugging Face",
    "LoRA",
    "QLoRA",
    "Vector search",
    "ChromaDB",
    "FAISS",
    "Pinecone",
    "Streamlit",
    "FastAPI",
    "Azure",
    "Data engineering",
    "AI evaluation",
    "Reranking",
    "Legacy modernisation",
    "System integration",
]


def build_candidate_profile() -> CandidateProfile:
    """Create a candidate profile using the existing Pydantic schema."""
    return CandidateProfile(
        name="Will Munda",
        summary=(
            "Senior software, data and AI engineer with extensive enterprise "
            "delivery experience and healthcare/life-sciences data engineering "
            "experience. Skills include Python, SQL Server, T-SQL, ETL/ELT, "
            "Snowflake Cortex, LLM applications, RAG, vector retrieval, "
            "clinical data integration and legacy-system modernisation. "
            "Seeking remote-first UK roles, including permanent and contract "
            "positions. Contract day-rate target: £450 minimum. Healthcare "
            "and life sciences are priority specialisms."
        ),
        skills=PREFERRED_SKILLS.copy(),
        preferred_titles=PREFERRED_TITLES.copy(),
        preferred_locations=PREFERRED_LOCATIONS.copy(),
        minimum_day_rate=450.0,
        years_experience=None,
        employment_types=["Permanent", "Contract"],
    )


def main() -> None:
    """Print the profile as JSON for inspection or debugging."""
    profile = build_candidate_profile()
    print(profile.model_dump_json(indent=2))


if __name__ == "__main__":
    main()
