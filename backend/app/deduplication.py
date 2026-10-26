import re
from urllib.parse import urlsplit


def dedup_key(org, mode):
    if mode == "name_address":
        return (
            (org.name.strip().casefold(), org.address.strip().casefold())
            if org.address
            else org.id
        )
    value = getattr(org, mode, None)
    if not value:
        return org.id
    if mode == "phone":
        return re.sub(r"\D", "", value)
    if mode == "website":
        return (
            (
                urlsplit(value if "://" in value else "https://" + value).hostname
                or value
            )
            .removeprefix("www.")
            .lower()
        )
    return value
