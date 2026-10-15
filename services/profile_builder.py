"""Transparent baseline profile extraction; no external model or data transfer."""
import re
from models import CandidateProfile

KNOWN_SKILLS = {
 "python", "sql", "t-sql", "sqlite", "postgresql", "snowflake", "pandas", "streamlit",
 "langchain", "langgraph", "rag", "llm", "machine learning", "pytorch", "tensorflow",
 "azure", "aws", "docker", "kubernetes", "etl", "elt", "dbt", "airflow", "fastapi",
 "rest api", "chroma", "faiss", "pinecone", "omop", "healthcare", "clinical data",
 "data engineering", "prompt engineering", "evaluation", "guardrails", "git", "linux"
}

def build_profile(cv_text: str) -> CandidateProfile:
    lowered = cv_text.lower()
    found = sorted(skill for skill in KNOWN_SKILLS if re.search(r"(?<![\w+#])" + re.escape(skill) + r"(?![\w+#])", lowered))
    title_lines = [line.strip() for line in cv_text.splitlines()[:12] if len(line.strip()) < 100]
    name = title_lines[0] if title_lines else "Candidate"
    years = re.search(r"(\d{1,2})\+?\s+years(?:'| of)?\s+(?:of\s+)?(?:experience|work)", lowered)
    return CandidateProfile(name=name[:100], summary=" ".join(cv_text.split())[:600], skills=found,
                            years_experience=float(years.group(1)) if years else None)
