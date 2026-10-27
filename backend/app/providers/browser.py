from __future__ import annotations
import asyncio, threading, time, re
from urllib.parse import urlsplit, parse_qs, unquote, quote
from .base import DataProvider, ProviderError
from ..models import Organization, FIELDS, CONTACTS
from ..browser.driver import browser_path, browser_service
from ..browser.scripts import (
    LIST_SCRIPT,
    SCROLL_SCRIPT,
    NEXT_SCRIPT,
    EXPAND_SCRIPT,
    CARD_SCRIPT,
)

CITIES = {
    "Москва": "moscow",
    "Санкт-Петербург": "spb",
    "Казань": "kazan",
    "Самара": "samara",
    "Екатеринбург": "ekaterinburg",
    "Новосибирск": "novosibirsk",
    "Краснодар": "krasnodar",
    "Нижний Новгород": "n_novgorod",
    "Уфа": "ufa",
    "Челябинск": "chelyabinsk",
    "Омск": "omsk",
    "Ростов-на-Дону": "rostov",
    "Воронеж": "voronezh",
    "Пермь": "perm",
    "Красноярск": "krasnoyarsk",
    "Волгоград": "volgograd",
    "Тюмень": "tyumen",
    "Иркутск": "irkutsk",
    "Сочи": "sochi",
    "Томск": "tomsk",
    "Саратов": "saratov",
    "Тула": "tula",
    "Ярославль": "yaroslavl",
    "Владивосток": "vladivostok",
    "Калининград": "kaliningrad",
}
BROWSER_FIELDS = {
    "name",
    "branch_id",
    "category",
    "categories",
    "city",
    "address",
    "url",
    "phone",
    "phones",
    "email",
    "emails",
    "website",
    "websites",
    "telegram",
    "whatsapp",
    "vk",
    "instagram",
    "reviews",
    "rating",
    "contact_score",
    "source",
    "fetched_at",
    "field_status",
}


def capabilities():
    return {
        "connected": bool(browser_path()),
        "fields": {k: k in BROWSER_FIELDS for k in FIELDS},
        "messages": [
            "Браузерный сбор без API-ключа. Только публичные видимые карточки в пределах полученного разрешения.",
            "Отсутствующие сведения остаются неизвестными. CAPTCHA требует вашего действия в окне браузера.",
        ],
        "browser": True,
        "browser_name": browser_path(),
    }


def search_url(city, category, keyword=""):
    slug = city.region_id or CITIES.get(city.name)
    if not slug or not re.fullmatch(r"[a-z0-9_-]{1,80}", slug):
        raise ProviderError(
            "Укажите город из списка или адрес его раздела 2ГИС в настройках географии."
        )
    return (
        "https://2gis.ru/"
        + slug
        + "/search/"
        + quote(" ".join(filter(None, [category, keyword])), safe="")
    )


def card_to_organization(card, city, category, weights=None):
    match = re.search(r"/firm/(\d+)", urlsplit(card.get("url", "")).path)
    if not match or not card.get("name"):
        raise ProviderError(
            "Не удалось прочитать название и ID карточки. Проверьте страницу 2ГИС."
        )
    identifier = match.group(1)
    o = Organization(
        id=identifier,
        branch_id=identifier,
        name=card["name"],
        category=card.get("category"),
        categories=[card["category"]] if card.get("category") else [],
        city=city,
        address=card.get("address") or None,
        url=card["url"].split("?")[0],
        source="2gis-browser",
    )
    contacts = {k: [] for k in CONTACTS}
    for link in card.get("links", []):
        url = link.get("url", "")
        label = link.get("label", "")
        prop = link.get("itemprop", "")
        parsed = urlsplit(url)
        host = (parsed.hostname or "").lower().removeprefix("www.")
        if parsed.scheme == "tel":
            if not re.search(r"\.\.\.|…", label):
                contacts["phone"].append(unquote(url[4:]))
            continue
        if parsed.scheme == "mailto":
            contacts["email"].append(unquote(url[7:].split("?")[0]))
            continue
        if parsed.scheme not in ("http", "https"):
            continue
        if host == "link.2gis.ru":
            target = parse_qs(parsed.query).get("url", [""])[0] or (
                unquote(parsed.query)
                if parsed.query.startswith(
                    ("http://", "https://", "http%3A", "https%3A")
                )
                else ""
            )
            if target:
                url = target
                parsed = urlsplit(url)
                host = (parsed.hostname or "").lower().removeprefix("www.")
                if parsed.scheme not in ("http", "https"):
                    continue
        social = next(
            (
                v
                for h, v in {
                    "t.me": "telegram",
                    "telegram.me": "telegram",
                    "wa.me": "whatsapp",
                    "api.whatsapp.com": "whatsapp",
                    "vk.com": "vk",
                    "instagram.com": "instagram",
                    "viber.com": "viber",
                    "max.ru": "max",
                    "facebook.com": "facebook",
                    "ok.ru": "ok",
                }.items()
                if host == h or host.endswith("." + h)
            ),
            None,
        )
        if social:
            contacts[social].append(url)
        elif (
            host
            and host
            not in (
                "2gis.ru",
                "law.2gis.ru",
                "dev.2gis.com",
                "apps.apple.com",
                "play.google.com",
            )
            and not host.endswith(".2gis.ru")
            and (
                prop == "url"
                or re.search(r"сайт|website", label, re.I)
                or host in label.lower().replace("www.", "")
            )
        ):
            contacts["website"].append(url)
    for field, values in contacts.items():
        values = list(dict.fromkeys(values))
        contacts[field] = values
        setattr(o, field, values[0] if values else None)
        o.field_status[field] = "present" if values else "unknown"
    if card.get("websiteAbsentExplicit") and not o.website:
        o.field_status["website"] = "absent"
    o.phones = contacts["phone"]
    o.emails = contacts["email"]
    o.websites = contacts["website"]
    for field in ["rating", "reviews"]:
        raw = str(card.get(field) or "").replace(",", ".").replace("\xa0", " ")
        number = re.search(r"\d+(?:\.\d+)?", raw.replace(" ", ""))
        if number:
            value = (
                float(number.group())
                if field == "rating"
                else int(float(number.group()))
            )
            if field == "reviews" or 0 <= value <= 5:
                setattr(o, field, value)
    for k, v in o.model_dump().items():
        if k not in o.field_status and k != "field_status":
            o.field_status[k] = "present" if v is not None and v != [] else "unknown"
    if o.reviews == 0:
        o.field_status["reviews"] = "absent"
    weights = weights or {
        "phone": 1,
        "website": 1,
        "email": 1,
        "telegram": 1,
        "whatsapp": 1,
    }
    total = sum(weights.values())
    o.contact_score = (
        round(
            100
            * sum(v for k, v in weights.items() if o.field_status.get(k) == "present")
            / total,
            1,
        )
        if total
        else 0
    )
    return o


class BrowserProvider(DataProvider):
    def __init__(self, service=None):
        self.service = service or browser_service
        self.state = {}
        self.cancelled = threading.Event()

    async def diagnose(self):
        result = capabilities()
        if not result["connected"]:
            raise ProviderError(
                "Не найден Microsoft Edge или Google Chrome. Установите один из них."
            )
        await asyncio.to_thread(self.service.open_home)
        return result

    def check(self, data=None):
        if self.cancelled.is_set():
            raise ProviderError("Поиск приостановлен", paused=True)
        if data and data.get("blocked"):
            raise ProviderError(
                "В браузере проверка или ограничение доступа. Выполните требуемое действие вручную в окне 2ГИС и нажмите «Продолжить».",
                paused=True,
            )

    def wait(self, seconds):
        if self.cancelled.wait(seconds):
            self.check()

    def read(self, tab, script):
        self.check()
        data = tab.evaluate(script)
        self.check(data)
        return data

    def load(self, tab, url, script, ready):
        tab.call("Page.bringToFront")
        current = tab.evaluate("location.href")
        if current.split("?")[0] != url.split("?")[0]:
            tab.navigate(url)
        deadline = time.monotonic() + 25
        while time.monotonic() < deadline:
            self.wait(0.3)
            try:
                data = self.read(tab, script)
            except ProviderError as error:
                if error.paused:
                    raise
                continue
            actual = urlsplit(data.get("url", ""))
            expected = urlsplit(url)
            same_page = actual.hostname == expected.hostname and unquote(
                actual.path
            ).rstrip("/") == unquote(expected.path).rstrip("/")
            if same_page and ready(data):
                return data
        raise ProviderError(
            "Карточка или выдача не загрузилась. Проверьте браузер и продолжите поиск.",
            paused=True,
        )

    def _page(self, spec, city, category, page):
        self.check()
        url = search_url(city, category, spec.keyword)
        key = url
        state = self.state.setdefault(key, {"links": [], "exhausted": False})
        search = self.service.tab("search")
        if page == 1 or page - 1 >= len(state["links"]):
            data = self.load(
                search,
                url,
                LIST_SCRIPT,
                lambda d: bool(d.get("links")) or d.get("empty"),
            )
            for link in data.get("links", []):
                if link["url"] not in state["links"]:
                    state["links"].append(link["url"])
            stale = 0
            while page - 1 >= len(state["links"]) and not state["exhausted"]:
                self.read(search, SCROLL_SCRIPT)
                self.wait(1)
                data = self.read(search, LIST_SCRIPT)
                before = len(state["links"])
                for link in data.get("links", []):
                    if link["url"] not in state["links"]:
                        state["links"].append(link["url"])
                if len(state["links"]) > before:
                    stale = 0
                    continue
                stale += 1
                if stale >= 3:
                    if self.read(search, NEXT_SCRIPT):
                        stale = 0
                        self.wait(1.5)
                    else:
                        state["exhausted"] = True
        index = page - 1
        if index >= len(state["links"]):
            return [], False
        details = self.service.tab("details")
        card_url = state["links"][index]
        data = self.load(
            details,
            card_url,
            CARD_SCRIPT,
            lambda d: d.get("ready") and bool(d.get("name")),
        )
        for _ in range(5):
            expanded = self.read(details, EXPAND_SCRIPT)
            if not expanded.get("clicked"):
                break
            self.wait(0.5)
        self.wait(0.5)
        data = self.read(details, CARD_SCRIPT)
        return [
            card_to_organization(data, city.name, category, spec.score_weights)
        ], index + 1 < len(state["links"]) or not state["exhausted"]

    async def page(self, spec, city, category, page):
        task = asyncio.create_task(
            asyncio.to_thread(self._page, spec, city, category, page)
        )
        try:
            return await asyncio.shield(task)
        except asyncio.CancelledError:
            self.cancelled.set()
            try:
                await task
            except (ProviderError, asyncio.CancelledError):
                pass
            raise
