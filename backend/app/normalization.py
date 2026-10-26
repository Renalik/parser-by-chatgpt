from urllib.parse import urlsplit
from .models import Organization, CONTACTS


def normalize(raw, city, weights=None, contacts_complete=False):
    cats = [r["name"] for r in raw.get("rubrics", []) if r.get("name")]
    point = raw.get("point") or {}
    reviews = raw.get("reviews") or {}
    adm = {a.get("type"): a.get("name") for a in raw.get("adm_div", [])}
    o = Organization(
        id=str(raw["id"]),
        branch_id=str(raw["id"]),
        org_id=str(raw["org"]["id"]) if raw.get("org", {}).get("id") else None,
        name=raw.get("name", "Без названия"),
        category=cats[0] if cats else None,
        categories=cats,
        city=adm.get("city") or city,
        region=adm.get("region"),
        district=adm.get("district"),
        address=raw.get("address_name"),
        latitude=point.get("lat"),
        longitude=point.get("lon"),
        url="https://2gis.ru/firm/" + str(raw["id"]),
        rating=reviews.get("general_rating"),
        reviews=reviews.get("general_review_count"),
        schedule=raw.get("schedule"),
        branch_count=raw.get("org", {}).get("branch_count"),
    )
    contacts = {k: [] for k in CONTACTS}
    for group in raw.get("contact_groups", []):
        for c in group.get("contacts", []):
            typ = c.get("type", "")
            value = c.get("value") or c.get("url")
            url = c.get("url") or value
            if not value:
                continue
            host = (
                urlsplit(url if "://" in url else "https://" + url).hostname or ""
            ).lower()
            social = next(
                (
                    v
                    for k, v in {
                        "t.me": "telegram",
                        "telegram.me": "telegram",
                        "wa.me": "whatsapp",
                        "api.whatsapp.com": "whatsapp",
                        "vk.com": "vk",
                        "instagram.com": "instagram",
                        "facebook.com": "facebook",
                        "ok.ru": "ok",
                        "max.ru": "max",
                        "viber.com": "viber",
                    }.items()
                    if host == k or host.endswith("." + k)
                ),
                None,
            )
            target = social or {
                "phone": "phone",
                "email": "email",
                "website": "website",
            }.get(typ)
            if target:
                contacts[target].append(value if target in ("phone", "email") else url)
    for k, values in contacts.items():
        setattr(o, k, values[0] if values else None)
        o.field_status[k] = (
            "present"
            if values
            else (
                "absent" if contacts_complete and "contact_groups" in raw else "unknown"
            )
        )
    o.phones = contacts["phone"]
    o.emails = contacts["email"]
    o.websites = contacts["website"]
    for k, v in o.model_dump().items():
        if k not in o.field_status and k != "field_status":
            o.field_status[k] = "present" if v is not None and v != [] else "unknown"
    if o.reviews == 0:
        o.field_status["reviews"] = "absent"
    if o.rating == 0:
        o.field_status["rating"] = "absent"
    weights = weights or {
        "phone": 1,
        "email": 1,
        "website": 1,
        "telegram": 1,
        "whatsapp": 1,
    }
    total = sum(weights.values())
    o.contact_score = (
        round(
            100
            * sum(w for k, w in weights.items() if o.field_status.get(k) == "present")
            / total,
            1,
        )
        if total
        else 0
    )
    return o
