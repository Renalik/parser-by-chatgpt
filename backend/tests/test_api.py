from fastapi.testclient import TestClient
from backend.app.api import app


def test_no_key_and_no_fictional_results():
    with TestClient(app) as c:
        assert not c.get("/api/meta").json()["has_key"]
        r = c.post(
            "/api/jobs",
            json={
                "cities": [{"name": "Москва", "region_id": "32"}],
                "categories": ["Кафе"],
            },
        )
        assert r.status_code == 400 and c.get("/api/jobs").json() == []


def test_templates_and_column_presets():
    with TestClient(app) as c:
        spec = {"mode": "demo", "cities": [{"name": "Казань"}], "categories": ["Кафе"]}
        t = c.post("/api/templates", json={"name": "Тест", "value": spec}).json()
        assert c.get("/api/templates").json()[0]["id"] == t["id"]
        assert c.delete("/api/templates/" + t["id"]).status_code == 200
        t = c.post(
            "/api/templates",
            json={
                "name": "CRM",
                "kind": "export",
                "value": {"columns": ["phone", "name"], "format": "csv"},
            },
        )
        assert t.status_code == 200


def test_csrf_origin_and_license():
    with TestClient(app) as c:
        assert (
            c.post(
                "/api/connection",
                json={"mode": "demo"},
                headers={"Origin": "https://evil.example"},
            ).status_code
            == 403
        )
        assert c.get("/api/meta").json()["license"]["export_allowed"] is False
        assert (
            c.put(
                "/api/license", json={"storage_allowed": True, "export_allowed": False}
            ).status_code
            == 200
        )


def test_demo_workflow_and_export():
    import time

    with TestClient(app) as c:
        assert c.post("/api/connection", json={"mode": "demo"}).json()["connected"]
        j = c.post(
            "/api/jobs",
            json={
                "mode": "demo",
                "cities": [{"name": "Москва"}],
                "categories": ["Кафе"],
                "limit": 10,
                "requests_per_second": 5,
            },
        ).json()
        for _ in range(30):
            if c.get("/api/jobs/" + j["id"]).json()["status"] == "completed":
                break
            time.sleep(0.05)
        assert c.get("/api/jobs/" + j["id"]).json()["matched"] == 10
        rows = c.get("/api/jobs/" + j["id"] + "/results").json()["items"]
        assert len(rows) == 10
        r = c.post(
            "/api/jobs/" + j["id"] + "/export",
            json={"columns": ["name", "phone"], "format": "xlsx"},
        )
        assert r.status_code == 200 and r.content[:2] == b"PK"
        assert (
            c.post(
                "/api/jobs/" + j["id"] + "/remove-rows", json={"ids": [rows[0]["id"]]}
            ).status_code
            == 200
        )
        assert c.get("/api/jobs/" + j["id"]).json()["matched"] == 9
        assert c.delete("/api/jobs/" + j["id"]).status_code == 200
