import asyncio
from uuid import uuid4
from datetime import datetime, timedelta, timezone
from . import database as db
from .models import SearchSpec, Organization, now
from .providers.demo import DemoProvider
from .providers.dgis import DgisProvider
from .providers.browser import BrowserProvider, capabilities
from .providers.base import ProviderError
from .filters import matches
from .deduplication import dedup_key
from .settings import settings


class JobManager:
    def __init__(self):
        self.tasks = {}
        self.key = settings.dgis_api_key
        self.caps = {}
        self.mode = "browser"
        self.caps = capabilities()

    def provider(self, mode):
        if mode == "browser":
            return BrowserProvider()
        return DemoProvider() if mode == "demo" else DgisProvider(self.key, self.caps)

    def recover(self):
        for job in db.all_records("job"):
            if job["mode"] in ("live", "browser") and datetime.fromisoformat(
                job["created_at"]
            ) < datetime.now(timezone.utc) - timedelta(days=settings.retention_days):
                db.delete(job["id"])
                continue
            if job["status"] in ("running", "queued"):
                job["status"] = "paused"
                job["message"] = "Приостановлено после перезапуска. Можно продолжить."
                db.put("job", job["id"], job)

    def create(self, spec):
        job = {
            "id": str(uuid4()),
            "name": spec.name,
            "mode": spec.mode,
            "spec": spec.model_dump(),
            "created_at": now(),
            "status": "queued",
            "results": [],
            "processed": 0,
            "duplicates": 0,
            "excluded": 0,
            "requests": 0,
            "cursor": {"city": 0, "category": 0, "page": 1},
            "seen": [],
            "resolved": {},
            "message": "",
            "progress": 0,
        }
        db.put("job", job["id"], job)
        self.launch(job["id"])
        return job

    def launch(self, id):
        if id in self.tasks and not self.tasks[id].done():
            return
        self.tasks[id] = asyncio.create_task(self.run(id))

    async def shutdown(self):
        for task in self.tasks.values():
            task.cancel()
        await asyncio.gather(*self.tasks.values(), return_exceptions=True)
        from .browser.driver import browser_service

        await asyncio.to_thread(browser_service.close)

    async def run(self, id):
        job = db.get(id)
        spec = SearchSpec.model_validate(job["spec"])
        provider = self.provider(spec.mode)
        if spec.mode == "browser":
            provider.state = job.setdefault("browser_state", {})
        job["status"] = "running"
        job["message"] = ""
        db.put("job", id, job)
        try:
            for ci in range(job["cursor"]["city"], len(spec.cities)):
                city = spec.cities[ci]
                if spec.mode == "live" and not city.region_id:
                    raise ProviderError("Выберите город из справочника регионов 2ГИС")
                startcat = (
                    job["cursor"]["category"] if ci == job["cursor"]["city"] else 0
                )
                for ki in range(startcat, len(spec.categories)):
                    category = spec.categories[ki]
                    resolved = category
                    if spec.mode == "live":
                        cache = f"{city.region_id}:{category}"
                        if cache not in job["resolved"]:
                            if job["requests"] >= spec.request_limit:
                                raise ProviderError("Достигнут лимит запросов задачи")
                            job["requests"] += 1
                            db.put("job", id, job)
                            await asyncio.sleep(1 / spec.requests_per_second)
                            rubrics = await provider.categories(
                                category, city.region_id
                            )
                            exact = [
                                r
                                for r in rubrics
                                if r.get("name", "").casefold() == category.casefold()
                            ]
                            if len(exact) != 1:
                                raise ProviderError(
                                    f"Уточните категорию «{category}» через справочник: точная рубрика не определена."
                                )
                            job["resolved"][cache] = str(exact[0]["id"])
                        resolved = job["resolved"][cache]
                    page = (
                        job["cursor"]["page"]
                        if ci == job["cursor"]["city"]
                        and ki == job["cursor"]["category"]
                        else 1
                    )
                    while True:
                        current = db.get(id)
                        if not current or current["status"] != "running":
                            return
                        job["cursor"] = {"city": ci, "category": ki, "page": page}
                        for attempt in range(3):
                            if job["requests"] >= spec.request_limit:
                                raise ProviderError(
                                    "Достигнут лимит запросов задачи. Создайте копию с большим лимитом."
                                )
                            job["requests"] += 1
                            db.put("job", id, job)
                            await asyncio.sleep(
                                max(
                                    1 / spec.requests_per_second,
                                    2**attempt if attempt else 0,
                                )
                            )
                            try:
                                rows, more = await provider.page(
                                    spec, city, resolved, page
                                )
                                break
                            except ProviderError as error:
                                if not error.retryable or attempt == 2:
                                    raise
                        current = db.get(id)
                        if not current or current["status"] != "running":
                            return
                        for org in rows:
                            job["processed"] += 1
                            key = str(dedup_key(org, spec.dedup))
                            if key in job["seen"]:
                                job["duplicates"] += 1
                                continue
                            job["seen"].append(key)
                            if any(
                                x.casefold() in [c.casefold() for c in org.categories]
                                for x in spec.excluded_categories
                            ) or not matches(spec.filters, org, spec.unknown):
                                job["excluded"] += 1
                                continue
                            job["results"].append(org.model_dump())
                            if len(job["results"]) >= spec.limit:
                                break
                        job["cursor"]["page"] = page + 1
                        job["progress"] = min(
                            99,
                            round(
                                100
                                * (
                                    (ci * len(spec.categories) + ki)
                                    / (len(spec.cities) * len(spec.categories))
                                )
                            ),
                        )
                        db.put("job", id, job)
                        if len(job["results"]) >= spec.limit:
                            job["status"] = "completed"
                            job["progress"] = 100
                            db.put("job", id, job)
                            return
                        if not more:
                            break
                        page += 1
                    job["cursor"] = {"city": ci, "category": ki + 1, "page": 1}
                    db.put("job", id, job)
                job["cursor"] = {"city": ci + 1, "category": 0, "page": 1}
                db.put("job", id, job)
            job["status"] = "completed"
            job["progress"] = 100
        except asyncio.CancelledError:
            return
        except ProviderError as e:
            job["status"] = "paused" if e.paused else "failed"
            job["message"] = str(e)
        except Exception:
            job["status"] = "failed"
            job["message"] = (
                "Ошибка обработки данных. Задача сохранена; проверьте параметры и доступ API."
            )
        db.put("job", id, job)

    async def control(self, id, action):
        job = db.get(id)
        if not job:
            return None
        if action in ("pause", "stop"):
            job["status"] = "paused" if action == "pause" else "stopped"
            db.put("job", id, job)
            t = self.tasks.get(id)
            if t and not t.done():
                t.cancel()
                await asyncio.gather(t, return_exceptions=True)
        elif action == "resume" and job["status"] in ("paused", "stopped", "failed"):
            self.launch(id)
        return db.get(id)


manager = JobManager()
