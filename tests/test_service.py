from __future__ import annotations

from typing import Any

from hun_climate_policy.service import ClimatePolicyService


class FakeProvider:
    def __init__(self, metadata: list[dict[str, Any]]) -> None:
        self._metadata = metadata
        self.calls: list[tuple[str, int, int, float | None]] = []

    def metadata(self, no_cache: bool = False) -> list[dict[str, Any]]:
        return self._metadata

    def query(
        self, sql: str, page: int, page_size: int, timeout: float | None = None
    ) -> list[dict[str, Any]]:
        self.calls.append((sql, page, page_size, timeout))
        return [{"inventory_year": 2022, "n": 1}]

    @staticmethod
    def query_hash(sql: str) -> str:
        return "fixture-hash"


def test_discovery_filters_to_profile(metadata_fixture: list[dict[str, Any]]) -> None:
    service = ClimatePolicyService(provider=FakeProvider(metadata_fixture))
    assert [row["database"] for row in service.list_databases()] == ["GHG_Inventory", "GHGPAMS"]
    table = service.describe_table("GHG_Inventory", "latest", "ghg_value")
    assert table.logical_key == [
        "country_code",
        "submission_version",
        "inventory_year",
        "variable_uid",
    ]
    assert table.joins[0]["to"].endswith("ghg_variable")


def test_query_returns_provenance(metadata_fixture: list[dict[str, Any]]) -> None:
    provider = FakeProvider(metadata_fixture)
    service = ClimatePolicyService(provider=provider)
    result = service.query_sql(
        "SELECT inventory_year, COUNT(*) AS n FROM [GHG_Inventory].[latest].[ghg_value] "
        "WHERE country_code='HU' GROUP BY inventory_year",
        max_rows=10,
        page_size=5,
    )
    assert result.provenance.reporting_status == "reported_actual"
    assert result.provenance.query_hash == "fixture-hash"
    assert result.returned_rows == 1
    assert "TOP 10" in provider.calls[0][0]


def test_distinct_validates_column(metadata_fixture: list[dict[str, Any]]) -> None:
    service = ClimatePolicyService(provider=FakeProvider(metadata_fixture))
    try:
        service.list_distinct_values("GHG_Inventory", "latest", "ghg_value", "missing")
    except ValueError as exc:
        assert "Unknown column" in str(exc)
    else:
        raise AssertionError("expected ValueError")
