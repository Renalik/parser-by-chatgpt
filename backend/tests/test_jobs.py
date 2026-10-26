import asyncio
import pytest
from backend.app.jobs import manager, JobManager
from backend.app import database as db
from backend.app.models import SearchSpec
from backend.app.providers.base import ProviderError


def spec(**kw):
    return SearchSpec(
        cities=[{"name": "Москва"}, {"name": "Казань"}],
        categories=["Кафе", "Пекарни"],
        mode="demo",
        requests_per_second=5,
        limit=1000,
        **kw
    )


async def finish(id):
    await asyncio.wait_for(manager.tasks[id], 20)
    return db.get(id)


async def test_multicity_multicategory_pagination():
    j = manager.create(spec())
    j = await finish(j["id"])
    assert j["status"] == "completed"
    assert len(j["results"]) == 120
    assert j["requests"] == 12
    assert {r["city"] for r in j["results"]} == {"Москва", "Казань"}
    assert {r["category"] for r in j["results"]} == {"Кафе", "Пекарни"}


async def test_pause_resume_durable_cursor():
    j = manager.create(spec())
    await asyncio.sleep(0.4)
    await manager.control(j["id"], "pause")
    paused = db.get(j["id"])
    count = paused["processed"]
    await asyncio.sleep(0.2)
    assert db.get(j["id"])["processed"] == count
    await manager.control(j["id"], "resume")
    j = await finish(j["id"])
    assert j["status"] == "completed"
    assert len({r["id"] for r in j["results"]}) == 120


async def test_filter_website_and_telegram():
    j = manager.create(
        spec(
            filters={
                "conditions": [
                    {"field": "website", "op": "absent"},
                    {"field": "telegram", "op": "present"},
                ]
            }
        )
    )
    j = await finish(j["id"])
    assert len(j["results"]) == 16
    assert all(
        r["field_status"]["website"] == "absent" and r["telegram"] for r in j["results"]
    )


async def test_errors_and_request_limit():
    j = manager.create(spec(request_limit=1))
    j = await finish(j["id"])
    assert j["status"] == "failed"
    assert j["requests"] == 1


async def test_empty_response(monkeypatch):
    from backend.app.providers.demo import DemoProvider

    async def empty(*args):
        return [], False

    monkeypatch.setattr(DemoProvider, "page", empty)
    j = manager.create(spec())
    j = await finish(j["id"])
    assert j["status"] == "completed" and j["results"] == []


def test_restart_pauses_running_jobs():
    db.put(
        "job",
        "x",
        {
            "id": "x",
            "status": "running",
            "mode": "demo",
            "created_at": "2026-10-26T00:00:00+00:00",
        },
    )
    JobManager().recover()
    assert db.get("x")["status"] == "paused"
