import asyncio, hashlib
from .base import DataProvider
from ..models import FIELDS, CONTACTS
from ..normalization import normalize


class DemoProvider(DataProvider):
    async def diagnose(self):
        return {
            "connected": True,
            "fields": {
                k: True for k in FIELDS if k not in ["opening_date", "has_photos"]
            },
            "messages": ["Демонстрационные данные. Не являются организациями из 2ГИС."],
            "requests": 0,
        }

    async def page(self, spec, city, category, page):
        await asyncio.sleep(0.12)
        rows = []
        for i in range((page - 1) * 10, min(page * 10, 30)):
            uid = hashlib.sha256(f"{city.name}:{category}:{i}".encode()).hexdigest()[
                :16
            ]
            contacts = [{"type": "phone", "value": f"+7 (000) 000-{i:02d}-00"}]
            if i % 3:
                contacts.append(
                    {"type": "website", "value": f"https://example.org/demo/{i}"}
                )
            if i % 2:
                contacts.append(
                    {"type": "website", "value": f"https://t.me/example_demo_{i}"}
                )
            if i % 4:
                contacts.append({"type": "email", "value": f"demo{i}@example.org"})
            raw = {
                "id": uid,
                "name": f'{["Точка","Линия","Место","Контур","Среда"][i%5]} · пример {i+1}',
                "rubrics": [{"name": category}],
                "address_name": f"Учебная улица, {i+1}",
                "point": {"lat": 55.75 + i * 0.001, "lon": 37.61},
                "reviews": {
                    "general_rating": round(3 + (i % 20) / 10, 1),
                    "general_review_count": i * 3,
                },
                "org": {"id": uid, "branch_count": 1},
                "contact_groups": [{"contacts": contacts}],
            }
            if i % 7 == 0:
                raw.pop("contact_groups")
            o = normalize(raw, city.name, spec.score_weights, contacts_complete=True)
            o.source = "demo"
            o.url = None
            rows.append(o)
        return rows, page < 3
