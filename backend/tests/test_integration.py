import os, pytest
from backend.app.providers.dgis import DgisProvider


@pytest.mark.integration
@pytest.mark.skipif(
    not os.getenv("DGIS_INTEGRATION_KEY"),
    reason="DGIS_INTEGRATION_KEY не задан; реальный API не проверен",
)
async def test_live_key_diagnostic():
    result = await DgisProvider(os.environ["DGIS_INTEGRATION_KEY"]).diagnose()
    assert result["connected"] and result["fields"]["name"]
