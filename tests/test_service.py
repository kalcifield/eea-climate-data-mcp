from __future__ import annotations

from typing import Any

from eu_climate_policy.service import ClimatePolicyService


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
        "WHERE country_code='DE' GROUP BY inventory_year",
        max_rows=10,
        page_size=5,
    )
    assert result.provenance.reporting_status == "reported_actual"
    assert result.provenance.query_hash == "fixture-hash"
    assert result.returned_rows == 1
    assert "TOP 10" in provider.calls[0][0]


class SeriesFakeProvider(FakeProvider):
    def query(
        self, sql: str, page: int, page_size: int, timeout: float | None = None
    ) -> list[dict[str, Any]]:
        self.calls.append((sql, page, page_size, timeout))
        if "ghg_variable" in sql:
            return [
                {
                    "variable_uid": "uid-total",
                    "variable_name": "[Sectors/Totals][...][Total (without LULUCF)]",
                    "unit": "kt CO₂ equivalent",
                    "classification": "no classification",
                    "navigation": "Sectors/Totals",
                    "is_template": False,
                    "is_country_specific": False,
                }
            ]
        return [
            {"inventory_year": 2000, "value": 75.0},
            {"inventory_year": 1990, "value": 94.0},
            {"inventory_year": 1995, "value": None},
        ]


def test_emissions_series_sorts_client_side(metadata_fixture: list[dict[str, Any]]) -> None:
    provider = SeriesFakeProvider(metadata_fixture)
    service = ClimatePolicyService(provider=provider)
    result = service.get_emissions_series("DE", start_year=1990, end_year=2024)
    assert [point["year"] for point in result.series] == [1990, 2000]
    assert result.ordering == "year_ascending_client_side"
    assert result.variable_uid == "uid-total"
    assert any("sorted client-side" in w for w in result.provenance.warnings)
    assert all("ORDER BY" not in sql for sql, *_ in provider.calls)
    value_sql = provider.calls[-1][0]
    assert "uid-total" in value_sql
    assert "inventory_year >= 1990" in value_sql


def test_emissions_series_rejects_bad_scope(metadata_fixture: list[dict[str, Any]]) -> None:
    service = ClimatePolicyService(provider=SeriesFakeProvider(metadata_fixture))
    try:
        service.get_emissions_series("DE", accounting_scope="net")
    except ValueError as exc:
        assert "accounting_scope" in str(exc)
    else:
        raise AssertionError("expected ValueError")


def test_distinct_validates_column(metadata_fixture: list[dict[str, Any]]) -> None:
    service = ClimatePolicyService(provider=FakeProvider(metadata_fixture))
    try:
        service.list_distinct_values("GHG_Inventory", "latest", "ghg_value", "missing")
    except ValueError as exc:
        assert "Unknown column" in str(exc)
    else:
        raise AssertionError("expected ValueError")
