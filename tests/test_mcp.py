import pytest

from eea_climate_data.mcp_server import build_server


@pytest.mark.asyncio
async def test_server_exposes_discovery_sql_and_provenance_tools() -> None:
    tools = await build_server().list_tools()
    assert [tool.name for tool in tools] == [
        "list_databases",
        "list_versions",
        "list_tables",
        "search_tables",
        "describe_table",
        "preview_rows",
        "list_distinct_values",
        "search_emission_sectors",
        "describe_emission_sector",
        "get_emissions_series",
        "list_measures",
        "get_measure",
        "get_sql_capabilities",
        "validate_sql",
        "explain_sql",
        "query_sql",
        "get_provenance",
        "describe_reporting_status",
    ]
