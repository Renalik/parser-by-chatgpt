import os, tempfile
from pathlib import Path

_test_dir = tempfile.TemporaryDirectory(prefix="parser-tests-")
os.environ["DATABASE_URL"] = "sqlite:///" + str(Path(_test_dir.name) / "test.db")
import pytest
from backend.app import database as db
from backend.app.jobs import manager


@pytest.fixture(autouse=True)
def clean():
    db.Base.metadata.drop_all(db.engine)
    db.Base.metadata.create_all(db.engine)
    manager.tasks = {}
    manager.key = ""
    manager.caps = {}
    manager.mode = "live"
    yield
