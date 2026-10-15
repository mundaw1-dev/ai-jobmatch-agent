"""LangGraph workflow: validate input, deterministically rank jobs, return evidence."""
from typing import TypedDict
from langgraph.graph import StateGraph, END
from models import CandidateProfile, JobPosting, MatchResult
from services.matcher import rank_jobs

class MatchState(TypedDict, total=False):
    profile: CandidateProfile
    jobs: list[JobPosting]
    results: list[MatchResult]
    error: str

def _validate(state: MatchState) -> MatchState:
    if not state.get("profile"): return {"error": "A candidate profile is required."}
    if not state.get("jobs"): return {"results": []}
    return {}

def _match(state: MatchState) -> MatchState:
    try: return {"results": rank_jobs(state["profile"], state.get("jobs", []))}
    except (KeyError, ValueError, TypeError) as exc: return {"error": f"Matching failed: {exc}"}

def build_workflow():
    graph = StateGraph(MatchState)
    graph.add_node("validate", _validate)
    graph.add_node("match", _match)
    graph.set_entry_point("validate")
    graph.add_conditional_edges("validate", lambda s: "done" if s.get("error") or not s.get("jobs") else "match", {"done": END, "match": "match"})
    graph.add_edge("match", END)
    return graph.compile()

workflow = build_workflow()

def run_matching(profile: CandidateProfile, jobs: list[JobPosting]) -> list[MatchResult]:
    state = workflow.invoke({"profile": profile, "jobs": jobs})
    if state.get("error"): raise ValueError(state["error"])
    return state.get("results", [])
