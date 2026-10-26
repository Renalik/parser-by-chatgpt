import base64, secrets
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Literal
from uuid import uuid4
from fastapi import FastAPI, HTTPException, Request, Query
from fastapi.responses import Response, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.trustedhost import TrustedHostMiddleware
from pydantic import BaseModel, Field
from .settings import settings
from .jobs import manager
from . import database as db
from .models import SearchSpec, ExportSpec, FIELDS
from .filters import fields_used
from .export import export_rows
from .categories import PRESETS
from .providers.base import ProviderError


@asynccontextmanager
async def lifespan(app):
    manager.recover()
    yield
    await manager.shutdown()


app = FastAPI(title="2GIS Business Parser", lifespan=lifespan)
app.add_middleware(
    TrustedHostMiddleware, allowed_hosts=settings.allowed_hosts.split(",")
)


@app.middleware("http")
async def security(request: Request, call_next):
    if request.method not in ("GET", "HEAD", "OPTIONS"):
        origin = request.headers.get("origin")
        if origin and origin.rstrip("/") != str(request.base_url).rstrip("/"):
            # Vite development proxy keeps the original host.
            return JSONResponse({"detail": "Запрос с другого сайта запрещён"}, 403)
    if settings.app_password and request.url.path != "/api/health":
        header = request.headers.get("authorization", "")
        password = ""
        try:
            if header.startswith("Basic "):
                password = base64.b64decode(header[6:]).decode().split(":", 1)[1]
        except Exception:
            pass
        if not secrets.compare_digest(
            password.encode(), settings.app_password.encode()
        ):
            return Response(
                status_code=401,
                headers={"WWW-Authenticate": 'Basic realm="Business Parser"'},
            )
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "no-referrer"
    if request.url.path.startswith("/api"):
        response.headers["Cache-Control"] = "no-store"
    return response


@app.exception_handler(ProviderError)
async def provider_error(req, exc):
    return JSONResponse({"detail": str(exc)}, status_code=400)


def require_job(id):
    job = db.get(id)
    if not job or "spec" not in job:
        raise HTTPException(404, "Задача не найдена")
    return job


def summary(job):
    return {
        k: v for k, v in job.items() if k not in ("results", "seen", "resolved")
    } | {"matched": len(job["results"])}


def config():
    return db.get("settings") or {
        "storage_allowed": False,
        "export_allowed": False,
        "license_note": "",
    }


class Connection(BaseModel):
    mode: Literal["live", "demo"] = "live"
    api_key: str | None = Field(default=None, max_length=1024)


class License(BaseModel):
    storage_allowed: bool = False
    export_allowed: bool = False
    license_note: str = Field(default="", max_length=500)


class Template(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    kind: Literal["search", "export"] = "search"
    value: dict


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/api/meta")
def meta():
    return {
        "fields": FIELDS,
        "categories": PRESETS,
        "mode": manager.mode,
        "has_key": bool(manager.key),
        "capabilities": manager.caps,
        "license": config(),
        "limitations": [
            "Точные границы районов, полигоны и исключаемые зоны: недоступны в этой версии.",
            "Дата открытия, фотографии и проверка доступности сайта: недоступны.",
            "Работа в заданное время и атрибуты услуг: недоступны.",
            "Подкатегории выбирайте отдельными рубриками из справочника.",
            "Тарифы и права на хранение определяются вашим договором с 2ГИС.",
        ],
    }


@app.post("/api/connection")
async def connect(body: Connection):
    if any(j["status"] in ("running", "queued") for j in db.all_records("job")):
        raise HTTPException(409, "Сначала приостановите активные задачи")
    from .providers.dgis import DgisProvider
    from .providers.demo import DemoProvider

    candidate_key = body.api_key.strip() if body.api_key is not None else manager.key
    caps = await (
        DemoProvider() if body.mode == "demo" else DgisProvider(candidate_key)
    ).diagnose()
    manager.key = candidate_key
    manager.mode = body.mode
    manager.caps = caps
    return caps


@app.put("/api/license")
def license(body: License):
    db.put("settings", "settings", body.model_dump())
    return body


@app.get("/api/regions")
async def regions(q: str = Query(min_length=2, max_length=100)):
    if manager.mode == "demo":
        return [
            {"id": x, "name": x}
            for x in [
                "Москва",
                "Санкт-Петербург",
                "Казань",
                "Самара",
                "Екатеринбург",
                "Новосибирск",
            ]
            if q.casefold() in x.casefold()
        ]
    return await manager.provider("live").regions(q)


@app.get("/api/categories")
async def categories(q: str, region_id: str):
    if manager.mode == "demo":
        return [{"id": x, "name": x} for x in PRESETS if q.casefold() in x.casefold()]
    return await manager.provider("live").categories(q, region_id)


@app.get("/api/jobs")
def jobs():
    return sorted(
        [summary(j) for j in db.all_records("job")],
        key=lambda j: j["created_at"],
        reverse=True,
    )


@app.post("/api/jobs", status_code=201)
async def create(spec: SearchSpec):
    if spec.mode == "live":
        if (
            manager.mode != "live"
            or not manager.key
            or not manager.caps.get("connected")
        ):
            raise HTTPException(400, "Проверьте подключение к API в настройках")
        if not config()["storage_allowed"]:
            raise HTTPException(
                400,
                "Для поиска с сохранением результатов требуется разрешение на хранение по вашей лицензии",
            )
        if any(not c.region_id for c in spec.cities):
            raise HTTPException(400, "Выберите города из справочника")
        from .models import FilterGroup

        missing = []

        def validate_filters(group, all_and=True):
            all_and = all_and and group.logic == "AND"
            for condition in group.conditions:
                if isinstance(condition, FilterGroup):
                    validate_filters(condition, all_and)
                else:
                    native = {
                        "website": "has_site",
                        "reviews": "has_reviews",
                        "rating": "has_rating",
                        "has_photos": "has_photos",
                    }.get(condition.field)
                    can_native = (
                        all_and
                        and condition.op in ("present", "absent")
                        and native in manager.caps.get("native_filters", [])
                    )
                    if (
                        not manager.caps.get("fields", {}).get(condition.field)
                        and not can_native
                    ):
                        missing.append(FIELDS.get(condition.field, condition.field))

        validate_filters(spec.filters)
        if missing:
            raise HTTPException(400, "Недоступны поля фильтров: " + ", ".join(missing))
    if any(j["status"] in ("running", "queued") for j in db.all_records("job")):
        raise HTTPException(409, "Дождитесь завершения или приостановите текущий поиск")
    return summary(manager.create(spec))


@app.get("/api/jobs/{id}")
def get_job(id: str):
    return summary(require_job(id))


@app.post("/api/jobs/{id}/control/{action}")
async def control(id: str, action: Literal["pause", "resume", "stop"]):
    job = require_job(id)
    if action == "resume":
        if any(
            j["id"] != id and j["status"] in ("running", "queued")
            for j in db.all_records("job")
        ):
            raise HTTPException(409, "Уже выполняется другой поиск")
        if job["mode"] == "live" and (
            manager.mode != "live"
            or not manager.caps.get("connected")
            or not config()["storage_allowed"]
        ):
            raise HTTPException(400, "Проверьте подключение и разрешение на хранение")
    return summary(await manager.control(id, action))


@app.delete("/api/jobs/{id}")
async def delete_job(id: str):
    require_job(id)
    await manager.control(id, "stop")
    db.delete(id)
    return {"deleted": True}


@app.get("/api/jobs/{id}/results")
def results(
    id: str,
    q: str = "",
    sort: str = "name",
    desc: bool = False,
    page: int = Query(1, ge=1),
    size: int = Query(25, ge=1, le=100),
    presence: str = "all",
):
    job = require_job(id)
    rows = job["results"]
    if q:
        rows = [
            r
            for r in rows
            if q.casefold() in " ".join(str(v) for v in r.values()).casefold()
        ]
    if presence != "all":
        rows = [r for r in rows if r["field_status"].get("website") == presence]
    if sort not in FIELDS:
        raise HTTPException(400, "Неизвестная колонка")
    rows = sorted(
        rows,
        key=lambda r: (
            r.get(sort) is None,
            (
                r.get(sort)
                if isinstance(r.get(sort), (int, float))
                else str(r.get(sort, "")).casefold()
            ),
        ),
        reverse=desc,
    )
    stats = {
        k: sum(r["field_status"].get(k) == "present" for r in job["results"])
        for k in ["phone", "telegram", "website"]
    }
    stats.update(
        {
            f"website_{s}": sum(
                r["field_status"].get("website") == s for r in job["results"]
            )
            for s in ["absent", "unknown"]
        }
    )
    return {
        "items": rows[(page - 1) * size : page * size],
        "total": len(rows),
        "stats": stats,
    }


class Selection(BaseModel):
    ids: list[str]


@app.post("/api/jobs/{id}/remove-rows")
def remove_rows(id: str, body: Selection):
    job = require_job(id)
    if job["status"] in ("running", "queued"):
        raise HTTPException(409, "Приостановите поиск перед изменением результатов")
    job["results"] = [r for r in job["results"] if r["id"] not in body.ids]
    db.put("job", id, job)
    return summary(job)


@app.post("/api/jobs/{id}/export")
def export(id: str, spec: ExportSpec):
    job = require_job(id)
    if job["mode"] == "live" and not config()["export_allowed"]:
        raise HTTPException(403, "Экспорт не разрешён в настройках лицензии")
    content, mime = export_rows(job["results"], spec)
    return Response(
        content,
        media_type=mime,
        headers={
            "Content-Disposition": f'attachment; filename="organizations-{id[:8]}.{spec.format}"'
        },
    )


@app.get("/api/templates")
def templates():
    return db.all_records("template")


@app.post("/api/templates")
def save_template(body: Template):
    try:
        if body.kind == "search":
            SearchSpec.model_validate(body.value)
        else:
            ExportSpec.model_validate(body.value)
    except ValueError:
        raise HTTPException(422, "Неверные параметры шаблона") from None
    data = body.model_dump() | {"id": str(uuid4())}
    db.put("template", data["id"], data)
    return data


@app.delete("/api/templates/{id}")
def delete_template(id: str):
    if not any(t["id"] == id for t in db.all_records("template")):
        raise HTTPException(404, "Шаблон не найден")
    db.delete(id)
    return {"deleted": True}


static = Path(__file__).resolve().parents[2] / "frontend" / "dist"
if static.exists():
    app.mount("/", StaticFiles(directory=static, html=True), name="frontend")
