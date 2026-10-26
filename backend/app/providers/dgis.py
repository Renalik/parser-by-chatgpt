import asyncio
import httpx
from .base import DataProvider, ProviderError
from ..normalization import normalize
from ..models import FIELDS


class DgisProvider(DataProvider):
    base = "https://catalog.api.2gis.com"

    def __init__(self, key, capabilities=None, transport=None):
        self.key = key
        self.capabilities = capabilities or {}
        self.requests = 0
        self.transport = transport

    async def request(self, path, params):
        if not self.key:
            raise ProviderError("Укажите API-ключ в настройках")
        async with httpx.AsyncClient(
            timeout=20, follow_redirects=False, transport=self.transport
        ) as client:
            self.requests += 1
            try:
                r = await client.get(
                    self.base + path, params={**params, "key": self.key}
                )
            except httpx.HTTPError:
                raise ProviderError(
                    "Не удалось связаться с 2ГИС. Проверьте сеть и повторите поиск.",
                    True,
                ) from None
            if r.status_code == 429:
                raise ProviderError(
                    "Лимит API исчерпан (429). Уменьшите частоту и продолжите позже.",
                    True,
                )
            if r.status_code in (401, 403):
                raise ProviderError("API-ключ отклонён или недостаточно разрешений")
            if r.status_code >= 500:
                raise ProviderError("Временная ошибка сервиса 2ГИС", True)
            try:
                body = r.json()
            except ValueError:
                raise ProviderError("2ГИС вернул ответ неизвестного формата") from None
            code = body.get("meta", {}).get("code", r.status_code)
            if code not in (200, 201):
                raise ProviderError(
                    f"2ГИС отклонил запрос (код {code}). Проверьте разрешения и параметры."
                )
            return body.get("result", {})

    async def regions(self, q):
        return (await self.request("/2.0/region/search", {"q": q})).get("items", [])

    async def categories(self, q, region_id):
        return (
            await self.request(
                "/2.0/catalog/rubric/search", {"q": q, "region_id": region_id}
            )
        ).get("items", [])

    async def diagnose(self):
        result = await self.request(
            "/3.0/items", {"q": "Москва кафе", "type": "branch", "page_size": 1}
        )
        caps = {k: False for k in FIELDS}
        caps.update(
            {
                "name": True,
                "branch_id": True,
                "city": True,
                "url": True,
                "source": True,
                "fetched_at": True,
            }
        )
        messages = []
        mapping = {
            "items.contact_groups": [
                "phone",
                "email",
                "website",
                "telegram",
                "whatsapp",
                "vk",
                "instagram",
                "phones",
                "emails",
                "websites",
                "contact_score",
            ],
            "items.reviews": ["rating", "reviews"],
            "items.point": ["latitude", "longitude"],
            "items.rubrics": ["category", "categories"],
            "items.address": ["address"],
            "items.adm_div": ["region", "district"],
            "items.schedule": ["schedule"],
            "items.org": ["org_id", "branch_count"],
        }
        self.field_options = []
        for field, names in mapping.items():
            await asyncio.sleep(1)
            try:
                r = await self.request(
                    "/3.0/items",
                    {
                        "q": "Москва кафе",
                        "type": "branch",
                        "page_size": 1,
                        "fields": field,
                    },
                )
                items = r.get("items", [])
                rawfield = field.split(".")[-1]
                observed = bool(
                    items
                    and (
                        rawfield in items[0]
                        or (rawfield == "address" and "address_name" in items[0])
                    )
                )
                if observed:
                    self.field_options.append(field)
                    for name in names:
                        caps[name] = True
                else:
                    messages.append(
                        f"{field}: поле не подтверждено диагностическим ответом"
                    )
            except ProviderError:
                messages.append(f"{field}: доступ не подтверждён")
        native = []
        for parameter in ["has_site", "has_reviews", "has_rating", "has_photos"]:
            await asyncio.sleep(1)
            try:
                await self.request(
                    "/3.0/items",
                    {
                        "q": "Москва кафе",
                        "type": "branch",
                        "page_size": 1,
                        parameter: "true",
                    },
                )
                native.append(parameter)
            except ProviderError:
                messages.append(f"{parameter}: фильтр не подтверждён")
        return {
            "connected": True,
            "native_filters": native,
            "fields": caps,
            "request_fields": self.field_options,
            "messages": messages,
            "requests": self.requests,
            "regions": None,
            "categories": None,
        }

    async def page(self, spec, city, category, page):
        params = {
            "q": " ".join(
                filter(None, [city.name if not city.region_id else "", spec.keyword])
            ),
            "type": "branch",
            "page": page,
            "page_size": 10,
            "rubric_id": category,
        }
        if city.region_id:
            params["region_id"] = city.region_id
        if spec.point:
            params["point"] = spec.point
        if spec.radius:
            params["radius"] = spec.radius
        if self.capabilities.get("request_fields"):
            params["fields"] = ",".join(self.capabilities["request_fields"])
        native = {}

        def gather(group):
            if group.logic != "AND":
                return
            from ..models import FilterGroup

            for c in group.conditions:
                if isinstance(c, FilterGroup):
                    gather(c)
                elif c.field in (
                    "website",
                    "reviews",
                    "rating",
                    "has_photos",
                ) and c.op in ("present", "absent"):
                    name = {
                        "website": "has_site",
                        "reviews": "has_reviews",
                        "rating": "has_rating",
                        "has_photos": "has_photos",
                    }[c.field]
                    params[name] = "true" if c.op == "present" else "false"
                    native[c.field] = c.op

        gather(spec.filters)
        if not params.get("q"):
            params.pop("q", None)
        r = await self.request("/3.0/items", params)
        items = r.get("items", [])
        normalized = [normalize(x, city.name, spec.score_weights) for x in items]
        for org in normalized:
            for field, state in native.items():
                org.field_status[field] = state
        total = r.get("total", len(items))
        if page * 10 >= 500 and total > 500:
            raise ProviderError(
                "Достигнута глубина выдачи 500 записей для одной рубрики и города. Сузьте географию или фильтры; полнота поиска не подтверждена."
            )
        return normalized, page * 10 < total
