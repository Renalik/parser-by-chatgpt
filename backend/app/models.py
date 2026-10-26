from __future__ import annotations
from datetime import datetime, timezone
from typing import Literal, Any
from pydantic import BaseModel, Field, model_validator, ConfigDict

CONTACTS = [
    "phone",
    "email",
    "website",
    "telegram",
    "whatsapp",
    "vk",
    "instagram",
    "viber",
    "max",
    "facebook",
    "ok",
]
FIELDS = {
    "name": "Название",
    "category": "Категория",
    "city": "Город",
    "region": "Регион",
    "district": "Район",
    "address": "Адрес",
    "phone": "Телефон",
    "email": "Email",
    "website": "Сайт",
    "telegram": "Telegram",
    "whatsapp": "WhatsApp",
    "vk": "ВКонтакте",
    "instagram": "Instagram",
    "rating": "Рейтинг",
    "reviews": "Отзывы",
    "latitude": "Широта",
    "longitude": "Долгота",
    "url": "Ссылка на 2ГИС",
    "branch_id": "ID филиала",
    "org_id": "ID организации",
    "categories": "Все категории",
    "phones": "Все телефоны",
    "emails": "Все email",
    "websites": "Все сайты",
    "schedule": "Время работы",
    "branch_count": "Филиалов",
    "opening_date": "Дата открытия",
    "has_photos": "Фотографии",
    "contact_score": "Contact Score",
    "source": "Источник",
    "fetched_at": "Получено",
    "field_status": "Доступность полей",
}


def now():
    return datetime.now(timezone.utc).isoformat()


class Organization(BaseModel):
    id: str
    branch_id: str
    org_id: str | None = None
    name: str
    category: str | None = None
    categories: list[str] = Field(default_factory=list)
    city: str | None = None
    region: str | None = None
    district: str | None = None
    address: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    url: str | None = None
    phone: str | None = None
    email: str | None = None
    website: str | None = None
    telegram: str | None = None
    whatsapp: str | None = None
    vk: str | None = None
    instagram: str | None = None
    viber: str | None = None
    max: str | None = None
    facebook: str | None = None
    ok: str | None = None
    phones: list[str] = Field(default_factory=list)
    emails: list[str] = Field(default_factory=list)
    websites: list[str] = Field(default_factory=list)
    rating: float | None = None
    reviews: int | None = None
    has_photos: bool | None = None
    schedule: dict | None = None
    branch_count: int | None = None
    opening_date: str | None = None
    contact_score: float = 0
    source: str = "2gis"
    fetched_at: str = Field(default_factory=now)
    field_status: dict[str, str] = Field(default_factory=dict)


class Condition(BaseModel):
    model_config = ConfigDict(extra="forbid")
    field: str
    op: Literal[
        "present",
        "absent",
        "eq",
        "contains",
        "not_contains",
        "gte",
        "lte",
        "https",
        "domain",
        "not_domain",
    ]
    value: str | float | bool | None = None

    @model_validator(mode="after")
    def valid(self):
        if self.field not in Organization.model_fields:
            raise ValueError("Неизвестное поле фильтра")
        numeric = {
            "rating",
            "reviews",
            "branch_count",
            "latitude",
            "longitude",
            "contact_score",
        }
        urls = {"website", "telegram", "whatsapp", "vk", "instagram", "url"}
        if self.op in ("gte", "lte") and self.field not in numeric:
            raise ValueError("Числовой фильтр доступен только для числовых полей")
        if self.op in ("https", "domain", "not_domain") and self.field not in urls:
            raise ValueError("Условие домена доступно только для ссылок")
        if self.op in ("gte", "lte"):
            try:
                float(self.value)
            except (TypeError, ValueError):
                raise ValueError("Укажите число для сравнения")
        return self


class FilterGroup(BaseModel):
    model_config = ConfigDict(extra="forbid")
    logic: Literal["AND", "OR"] = "AND"
    conditions: list[Condition | FilterGroup] = Field(
        default_factory=list, max_length=40
    )


class Geography(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    region_id: str | None = None


class SearchSpec(BaseModel):
    name: str = Field(default="Новый поиск", min_length=1, max_length=150)
    mode: Literal["live", "demo"] = "live"
    cities: list[Geography] = Field(min_length=1, max_length=20)
    categories: list[str] = Field(min_length=1, max_length=25)
    excluded_categories: list[str] = Field(default_factory=list, max_length=25)
    keyword: str = Field(default="", max_length=200)
    point: str | None = None
    radius: int | None = Field(default=None, ge=1, le=40000)
    filters: FilterGroup = Field(default_factory=FilterGroup)
    unknown: Literal["exclude", "include"] = "exclude"
    dedup: Literal["branch_id", "org_id", "phone", "website", "name_address"] = (
        "branch_id"
    )
    limit: int = Field(default=100, ge=1, le=10000)
    request_limit: int = Field(default=100, ge=1, le=1000)
    requests_per_second: float = Field(default=1, gt=0, le=5)
    columns: list[str] = Field(
        default_factory=lambda: ["name", "city", "phone", "website", "url"]
    )
    score_weights: dict[str, float] = Field(
        default_factory=lambda: {
            "phone": 1,
            "email": 1,
            "website": 1,
            "telegram": 1,
            "whatsapp": 1,
        }
    )

    @model_validator(mode="after")
    def valid(self):
        if any(c not in FIELDS for c in self.columns):
            raise ValueError("Неизвестная колонка")
        if any(k not in CONTACTS or v < 0 for k, v in self.score_weights.items()):
            raise ValueError("Неверные веса Contact Score")
        if self.point:
            try:
                lon, lat = map(float, self.point.split(","))
                assert -180 <= lon <= 180 and -90 <= lat <= 90
            except Exception:
                raise ValueError("Координаты: долгота,широта")
        if self.radius and not self.point:
            raise ValueError("Для радиуса укажите координаты")
        return self


class ExportSpec(BaseModel):
    format: Literal["csv", "xlsx", "json"] = "xlsx"
    columns: list[str] = Field(min_length=1, max_length=40)
    headers: dict[str, str] = Field(default_factory=dict)
    ids: list[str] | None = None
    delimiter: Literal[";", ",", "\t"] = ";"
    bom: bool = True
    include_headers: bool = True
    empty: Literal["blank", "dash", "null"] = "blank"
    required: list[str] = Field(default_factory=list)
    metadata: bool = True
    width: int = Field(default=24, ge=8, le=80)

    @model_validator(mode="after")
    def valid(self):
        if len(set(self.columns)) != len(self.columns) or any(
            c not in FIELDS for c in self.columns + self.required
        ):
            raise ValueError("Неверные колонки")
        return self
