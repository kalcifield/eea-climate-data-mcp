from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP

from eu_climate_policy.factory import create_service


def build_server() -> FastMCP:
    mcp = FastMCP(
        "eu-climate-policy-mcp",
        instructions="Read-only, schema-aware access to European EEA climate data.",
    )
    svc = create_service()

    @mcp.tool()
    def list_databases(no_cache: bool = False) -> list[dict[str, Any]]:
        """List allowlisted EEA climate databases and available versions."""
        return svc.list_databases(no_cache)

    @mcp.tool()
    def list_versions(database: str) -> list[str]:
        """List version and revision aliases for an allowlisted database."""
        return svc.list_versions(database)

    @mcp.tool()
    def list_tables(database: str, version: str = "latest") -> list[dict[str, Any]]:
        """List tables in a database version."""
        return svc.list_tables(database, version)

    @mcp.tool()
    def search_tables(text: str) -> list[dict[str, str]]:
        """Search table names, descriptions, columns, and column descriptions."""
        return svc.search_tables(text)

    @mcp.tool()
    def describe_table(database: str, version: str, table: str) -> dict[str, Any]:
        """Describe schema, grain, keys, joins, reporting cycle, and caveats."""
        return svc.describe_table(database, version, table).model_dump(mode="json")

    @mcp.tool()
    def preview_rows(database: str, version: str, table: str, max_rows: int = 5) -> dict[str, Any]:
        """Preview a small bounded set of rows with provenance."""
        return svc.preview_rows(database, version, table, max_rows).model_dump(mode="json")

    @mcp.tool()
    def list_distinct_values(
        database: str, version: str, table: str, column: str, max_rows: int = 100
    ) -> dict[str, Any]:
        """List bounded distinct values after validating the column against metadata."""
        result = svc.list_distinct_values(database, version, table, column, max_rows)
        return result.model_dump(mode="json")

    @mcp.tool()
    def get_emissions_series(
        country: str,
        sector: str = "total",
        gas: str = "Aggregate GHGs",
        accounting_scope: str = "without_lulucf",
        start_year: int | None = None,
        end_year: int | None = None,
    ) -> dict[str, Any]:
        """Curated national GHG inventory time series with the statistically correct variable.

        country: ISO-style Discodata country code, e.g. 'HU', 'AT', 'EUA'.
        sector: 'total' or an IPCC sector number '1'..'6' (1 Energy, 2 IPPU,
        3 Agriculture, 4 LULUCF, 5 Waste, 6 Other).
        accounting_scope: 'with_lulucf' or 'without_lulucf' (totals only).
        Avoids TREND/BASE_YEAR_AVG/PREV_SUBMISSION variants; sorted client-side by year.
        """
        result = svc.get_emissions_series(
            country, sector, gas, accounting_scope, start_year, end_year
        )
        return result.model_dump(mode="json")

    @mcp.tool()
    def get_sql_capabilities() -> dict[str, Any]:
        """Return the documented and live-tested Discodata SQL capability matrix."""
        return svc.get_sql_capabilities()

    @mcp.tool()
    def validate_sql(sql: str, max_rows: int = 500) -> dict[str, Any]:
        """Parse and validate one allowlisted, read-only, bounded SELECT query."""
        return svc.validate_sql(sql, max_rows).model_dump(mode="json")

    @mcp.tool()
    def explain_sql(sql: str, max_rows: int = 500) -> dict[str, Any]:
        """Explain referenced objects, joins, filters, aggregations, and query risks."""
        return svc.explain_sql(sql, max_rows).model_dump(mode="json")

    @mcp.tool()
    def query_sql(
        sql: str,
        max_rows: int = 500,
        page: int = 1,
        page_size: int = 100,
        timeout: float = 30.0,
    ) -> dict[str, Any]:
        """Execute a locally validated and bounded SELECT, returning rows and provenance."""
        result = svc.query_sql(
            sql, max_rows=max_rows, page=page, page_size=page_size, timeout=timeout
        )
        return result.model_dump(mode="json")

    @mcp.tool()
    def get_provenance(sql: str, max_rows: int = 500) -> dict[str, Any]:
        """Preview provenance classification for a query without executing it."""
        return svc.get_provenance(sql, max_rows)

    @mcp.tool()
    def describe_reporting_status() -> dict[str, str]:
        """Explain reported actual, projection, policy estimate, and derived statuses."""
        return svc.describe_reporting_status()

    return mcp


def main() -> None:
    build_server().run(transport="stdio")


if __name__ == "__main__":
    main()
