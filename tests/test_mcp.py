import pytest

from hun_climate_policy.mcp_server import build_server


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
        "get_sql_capabilities",
        "validate_sql",
        "explain_sql",
        "query_sql",
        "get_provenance",
        "describe_reporting_status",
    ]
