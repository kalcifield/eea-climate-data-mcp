from __future__ import annotations

import httpx
import pytest
import respx

from eu_climate_policy.config import Settings
from eu_climate_policy.discodata import DiscodataError, DiscodataProvider


@respx.mock
def test_query_contract() -> None:
    route = respx.get("https://example.test/sql").mock(
        return_value=httpx.Response(200, json={"results": [{"x": 1}]})
    )
    provider = DiscodataProvider(Settings(base_url="https://example.test"))
    assert provider.query("SELECT TOP 1 1 AS x", 1, 1) == [{"x": 1}]
    assert route.called
    request = route.calls[0].request
    assert request.url.params["p"] == "1"
    assert request.url.params["nrOfHits"] == "1"


@respx.mock
def test_upstream_error_contract() -> None:
    respx.get("https://example.test/sql").mock(
        return_value=httpx.Response(
            200, json={"errors": [{"error": "not allowed", "errorcode": 10002}]}
        )
    )
    provider = DiscodataProvider(Settings(base_url="https://example.test"))
    with pytest.raises(DiscodataError) as error:
        provider.query("SELECT 1 AS x", 1, 1)
    assert error.value.code == 10002
