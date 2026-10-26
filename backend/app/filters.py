from urllib.parse import urlsplit
from .models import FilterGroup, Condition, Organization


def evaluate(rule, org: Organization):
    if isinstance(rule, FilterGroup):
        results = [evaluate(c, org) for c in rule.conditions]
        if not results:
            return True
        if rule.logic == "AND":
            return False if False in results else None if None in results else True
        return True if True in results else None if None in results else False
    value = getattr(org, rule.field, None)
    status = org.field_status.get(
        rule.field, "present" if value is not None and value != [] else "unknown"
    )
    if status == "unknown":
        return None
    if rule.op == "present":
        return status == "present"
    if rule.op == "absent":
        return status == "absent"
    if value is None:
        return False
    if rule.op == "eq":
        return str(value).casefold() == str(rule.value).casefold()
    if rule.op == "contains":
        return str(rule.value).casefold() in str(value).casefold()
    if rule.op == "not_contains":
        return str(rule.value).casefold() not in str(value).casefold()
    if rule.op == "gte":
        return float(value) >= float(rule.value)
    if rule.op == "lte":
        return float(value) <= float(rule.value)
    url = urlsplit(str(value) if "://" in str(value) else "https://" + str(value))
    if rule.op == "https":
        return str(value).startswith("https://")
    domain = (url.hostname or "").removeprefix("www.").lower()
    expected = str(rule.value).lower().removeprefix("www.")
    matches = domain == expected or domain.endswith("." + expected)
    return matches if rule.op == "domain" else not matches


def matches(group, org, unknown="exclude"):
    result = evaluate(group, org)
    return result is True or (result is None and unknown == "include")


def fields_used(group):
    result = set()
    for c in group.conditions:
        result |= fields_used(c) if isinstance(c, FilterGroup) else {c.field}
    return result
