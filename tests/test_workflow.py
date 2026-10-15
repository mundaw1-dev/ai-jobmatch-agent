from models import CandidateProfile, JobPosting
from graph.workflow import run_matching, workflow

def test_workflow_matches():
    p=CandidateProfile(skills=["Python"]); j=[JobPosting(id="1", title="Engineer", description="Python")]
    assert run_matching(p,j)[0].job.id == "1"

def test_workflow_empty_jobs():
    assert run_matching(CandidateProfile(), []) == []

def test_workflow_graph_compiles():
    assert workflow is not None
