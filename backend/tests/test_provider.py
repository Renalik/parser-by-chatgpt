import httpx, pytest
from backend.app.providers.dgis import DgisProvider
from backend.app.providers.base import ProviderError
from backend.app.models import SearchSpec


async def test_real_adapter_parameters_and_native_absence():
    calls = []

    def handler(req):
        calls.append(req)
        return httpx.Response(
            200,
            json={
                "meta": {"code": 200},
                "result": {
                    "total": 25,
                    "items": [{"id": "123", "name": "Кафе", "address_name": "Улица 1"}],
                },
            },
        )

    p = DgisProvider("test-not-secret", transport=httpx.MockTransport(handler))
    spec = SearchSpec(
        cities=[{"name": "Москва", "region_id": "32"}],
        categories=["Кафе"],
        filters={"conditions": [{"field": "website", "op": "absent"}]},
    )
    rows, more = await p.page(spec, spec.cities[0], "161", 2)
    assert more and rows[0].field_status["website"] == "absent"
    assert (
        calls[0].url.params["rubric_id"] == "161"
        and calls[0].url.params["region_id"] == "32"
    )
    assert (
        calls[0].url.params["has_site"] == "false"
        and calls[0].url.params["page"] == "2"
    )
    assert rows[0].field_status["phone"] == "unknown"


async def test_rate_limit_and_secret_not_in_error():
    p = DgisProvider(
        "test-not-secret",
        transport=httpx.MockTransport(lambda req: httpx.Response(429)),
    )
    with pytest.raises(ProviderError) as e:
        await p.request("/3.0/items", {})
    assert e.value.retryable and "test-not-secret" not in str(e.value)


async def test_unauthorized_no_retry():
    p = DgisProvider(
        "test-not-secret",
        transport=httpx.MockTransport(lambda req: httpx.Response(403)),
    )
    with pytest.raises(ProviderError) as e:
        await p.request("/3.0/items", {})
    assert not e.value.retryable
