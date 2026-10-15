import sqlite3
from pathlib import Path
from database import initialize_database, connect
from persistence.repositories import add_to_shortlist, load_shortlist
from models import JobPosting

def test_sqlite_uses_parameterized_storage(tmp_path):
    db=tmp_path/"test.db"; initialize_database(db)
    with connect(db) as conn:
        conn.execute("INSERT INTO jobs(id,job_json,source,saved_at) VALUES(?,?,?,?)", ("x' OR 1=1 --", "{}", "test", "now"))
        assert conn.execute("SELECT count(*) FROM jobs").fetchone()[0] == 1

def test_shortlist_round_trip(tmp_path, monkeypatch):
    import persistence.repositories as repo
    db=tmp_path/"short.db"
    monkeypatch.setattr(repo, "connect", lambda: connect(db))
    initialize_database(db)
    job=JobPosting(id="secure-1", title="Engineer", description="Python")
    add_to_shortlist(job, "Review terms")
    items=load_shortlist()
    assert items[0][0].id == "secure-1" and items[0][1] == "Review terms"
