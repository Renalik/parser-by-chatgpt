import asyncio
import pytest
from backend.app.providers.browser import (
    BrowserProvider,
    card_to_organization,
    search_url,
)
from backend.app.providers.base import ProviderError
from backend.app.models import SearchSpec, Geography
from backend.app.jobs import manager
from backend.app import database as db


def test_visible_contacts_and_redirect():
    card = {
        "url": "https://2gis.ru/moscow/firm/123",
        "name": "Компания",
        "category": "Кафе",
        "rating": "4,5",
        "reviews": "Отзывы 23",
        "links": [
            {"url": "tel:+70000000000", "label": "+7 000 000 00 00"},
            {
                "url": "https://link.2gis.ru/redirect?https://example.org",
                "label": "example.org",
            },
            {"url": "https://t.me/example", "label": "Telegram"},
        ],
    }
    o = card_to_organization(card, "Москва", "Кафе")
    assert o.website == "https://example.org" and o.telegram == "https://t.me/example"
    assert o.phone == "+70000000000" and o.reviews == 23 and o.rating == 4.5
    assert o.field_status["email"] == "unknown" and o.source == "2gis-browser"


def test_missing_website_and_truncated_phone_unknown():
    card = {
        "url": "https://2gis.ru/moscow/firm/123",
        "name": "Пример",
        "links": [{"url": "tel:+70000000000", "label": "+7 000 00..."}],
    }
    o = card_to_organization(card, "Москва", "Кафе")
    assert o.phone is None and o.field_status["website"] == "unknown"
    card["websiteAbsentExplicit"] = True
    assert (
        card_to_organization(card, "Москва", "Кафе").field_status["website"] == "absent"
    )


def test_browser_city_urls_are_restricted():
    assert search_url(Geography(name="Москва", region_id="moscow"), "Кафе").startswith(
        "https://2gis.ru/moscow/search/"
    )
    with pytest.raises(ProviderError):
        search_url(Geography(name="X", region_id="../../evil"), "Кафе")


def test_challenge_requires_user_action():
    with pytest.raises(ProviderError) as e:
        BrowserProvider().check({"blocked": True})
    assert e.value.paused and not e.value.retryable


async def test_browser_job_pauses_instead_of_failing(monkeypatch):
    async def blocked(*args):
        raise ProviderError("Проверка в браузере", paused=True)

    monkeypatch.setattr(BrowserProvider, "page", blocked)
    spec = SearchSpec(
        mode="browser",
        cities=[{"name": "Москва", "region_id": "moscow"}],
        categories=["Кафе"],
        requests_per_second=5,
    )
    job = manager.create(spec)
    await manager.tasks[job["id"]]
    saved = db.get(job["id"])
    assert saved["status"] == "paused" and saved["cursor"]["page"] == 1
    assert saved["results"] == []


async def test_cancel_waits_for_browser_action():
    import threading, time

    p = BrowserProvider()
    finished = threading.Event()

    def slow(*args):
        try:
            while not p.cancelled.wait(0.01):
                pass
            p.check()
        finally:
            finished.set()

    p._page = slow
    task = asyncio.create_task(p.page(None, None, None, 1))
    await asyncio.sleep(0.05)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert finished.is_set()


def test_navigation_does_not_read_previous_card():
    from backend.app.providers.browser import BrowserProvider

    class Tab:
        def __init__(self):
            self.reads = 0

        def call(self, *args):
            pass

        def navigate(self, url):
            pass

        def evaluate(self, script):
            if script == "location.href":
                return "https://2gis.ru/moscow/firm/100"
            self.reads += 1
            return {
                "url": "https://2gis.ru/moscow/firm/"
                + ("100" if self.reads == 1 else "200"),
                "name": "Name",
                "ready": True,
            }

    tab = Tab()
    provider = BrowserProvider()
    provider.wait = lambda t: None
    card = provider.load(
        tab, "https://2gis.ru/moscow/firm/200", "script", lambda d: d["ready"]
    )
    assert tab.reads == 2 and card["url"].endswith("/200")
