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


class SectorFakeProvider(FakeProvider):
    def query(
        self, sql: str, page: int, page_size: int, timeout: float | None = None
    ) -> list[dict[str, Any]]:
        self.calls.append((sql, page, page_size, timeout))
        if "ghg_variable" in sql and "DISTINCT" in sql:
            return [
                {"sector_number": "1.A.3", "navigation": "1.A.3. Transport", "sector": "1. Energy"},
                {
                    "sector_number": "1.A.3.b",
                    "navigation": "1.A.3.b. Road Transportation",
                    "sector": "1. Energy",
                },
                {"sector_number": "Sectors/Totals", "navigation": "Sectors/Totals", "sector": None},
            ]
        if "ghg_variable" in sql:
            return [
                {
                    "variable_uid": "uid-transport",
                    "variable_name": "[1.A.3. Transport][Fuels][Emissions][Aggregate GHGs]",
                    "unit": "kt CO₂ equivalent",
                    "classification": "Fuels",
                    "navigation": "1.A.3. Transport",
                    "is_template": False,
                    "is_country_specific": False,
                }
            ]
        return [{"inventory_year": 2024, "value": 14016.2}]


def test_subsector_series_resolves_transport(metadata_fixture: list[dict[str, Any]]) -> None:
    service = ClimatePolicyService(provider=SectorFakeProvider(metadata_fixture))
    result = service.get_emissions_series("HU", sector="1.A.3")
    assert result.variable_uid == "uid-transport"
    assert any("double counting" in w for w in result.provenance.warnings)


def test_sector_search_and_describe(metadata_fixture: list[dict[str, Any]]) -> None:
    service = ClimatePolicyService(provider=SectorFakeProvider(metadata_fixture))
    found = service.search_emission_sectors("transport")
    codes = {s["sector_code"]: s for s in found["sectors"]}
    assert set(codes) == {"1.A.3", "1.A.3.b"}
    assert codes["1.A.3.b"]["parent"] == "1.A.3"
    assert codes["1.A.3.b"]["level"] == 4
    described = service.describe_emission_sector("1.A.3")
    assert described["children"] == ["1.A.3.b"]
    assert any("double counting" in c for c in described["caveats"])


class PamsFakeProvider(FakeProvider):
    def query(
        self, sql: str, page: int, page_size: int, timeout: float | None = None
    ) -> list[dict[str, Any]]:
        self.calls.append((sql, page, page_size, timeout))
        return [
            {
                "Country": "Hungary",
                "ID_of_policy_or_measure": 4,
                "Name_of_policy_or_measure": "Renovation strategy",
                "Status_of_implementation": "Implemented",
                "Total_GHG_emissions_reductions_in_2030__kt_CO2eq_y_GHG": None,
                "Average_expost_emission_reduction__kt_CO2eq_y_GHG": None,
            }
        ]


def test_list_measures_builds_filters(metadata_fixture: list[dict[str, Any]]) -> None:
    provider = PamsFakeProvider(metadata_fixture)
    service = ClimatePolicyService(provider=provider)
    result = service.list_measures(country="Hungary", status="Implemented", sector="Transport")
    sql = provider.calls[0][0]
    assert "p.Country = 'Hungary'" in sql
    assert "p.Status_of_implementation = 'Implemented'" in sql
    assert "LIKE '%Transport%'" in sql
    assert any("not reported" in w for w in result.provenance.warnings)


def test_get_measure_flags_unreported_quantification(
    metadata_fixture: list[dict[str, Any]],
) -> None:
    service = ClimatePolicyService(provider=PamsFakeProvider(metadata_fixture))
    result = service.get_measure("Hungary", 4)
    quant = result["quantification"]
    assert quant["quantification_available"] is False
    assert quant["quantification_status"] == "not_reported"
    assert "not zero impact" in quant["warning"]
    assert result["measure"]["Name_of_policy_or_measure"] == "Renovation strategy"


def test_distinct_validates_column(metadata_fixture: list[dict[str, Any]]) -> None:
    service = ClimatePolicyService(provider=FakeProvider(metadata_fixture))
    try:
        service.list_distinct_values("GHG_Inventory", "latest", "ghg_value", "missing")
    except ValueError as exc:
        assert "Unknown column" in str(exc)
    else:
        raise AssertionError("expected ValueError")
