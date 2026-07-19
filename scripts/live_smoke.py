from __future__ import annotations

from hun_climate_policy.service import ClimatePolicyService


def main() -> None:
    service = ClimatePolicyService()
    databases = service.list_databases(no_cache=True)
    assert {row["database"] for row in databases} == {"GHG_Inventory", "GHGPAMS"}
    description = service.describe_table("GHG_Inventory", "latest", "ghg_value")
    assert "country_code" in {column.name for column in description.columns}
    result = service.query_sql(
        "SELECT v.inventory_year, COUNT(*) AS n "
        "FROM [GHG_Inventory].[latest].[ghg_value] AS v "
        "WHERE v.country_code='HU' GROUP BY v.inventory_year",
        max_rows=10,
        page_size=5,
    )
    assert result.results and result.provenance.reporting_status == "reported_actual"
    policies = service.query_sql(
        "SELECT TOP 2 Country, ID_of_policy_or_measure, Name_of_policy_or_measure "
        "FROM [GHGPAMS].[latest].[annexIX_flat_view_PaMs_elasticsearch] "
        "WHERE Country='Hungary'",
        max_rows=2,
        page_size=2,
    )
    assert policies.results and all(row["Country"] == "Hungary" for row in policies.results)
    print("live smoke: ok")


if __name__ == "__main__":
    main()
