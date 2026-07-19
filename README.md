# eea-climate-data-mcp

[![eu-climate — Europe’s climate reports, made queryable](assets/eu-climate-hero.png)](assets/eu-climate-hero.png)

[![PyPI](https://img.shields.io/pypi/v/eea-climate-data-mcp)](https://pypi.org/project/eea-climate-data-mcp/)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![MCP](https://img.shields.io/badge/MCP-stdio-6f42c1)](https://modelcontextprotocol.io/)
[![Status: Alpha](https://img.shields.io/badge/status-alpha-orange)](TODO.md)
[![Data: EEA Discodata](https://img.shields.io/badge/data-EEA%20Discodata-0097a7)](https://discodata.eea.europa.eu/)

Schema-aware, read-only access to European climate data published through the public
Discodata service of the European Environment Agency (EEA).

This MVP is a **conditional go**. It supports the verified GHG Inventory and Policies
and Measures databases. A current projections database was not visible in Discodata
metadata during the 2026-07-19 spike, so WEM/WAM comparison is not claimed.

> [!IMPORTANT]
> This is an independent, unofficial client. The EEA and reporting countries remain
> the authoritative sources.

> [!WARNING]
> This repository is an experimental proof of concept, not a production service.
> Interfaces, upstream schemas, and the undocumented execution allowlist may change.
> See [`TODO.md`](TODO.md).

## Install

Install the CLI and MCP server as isolated commands:

```bash
uv tool install eea-climate-data-mcp
eu-climate --help
```

Development checkout:

```bash
uv sync --extra test
uv run eu-climate databases list
uv run eea-climate-data-mcp
```

The MCP command uses stdio transport. No credentials are required.

Claude Code:

```bash
claude mcp add --scope user eu-climate -- uvx eea-climate-data-mcp
```

Codex CLI:

```bash
codex mcp add eu-climate -- uvx eea-climate-data-mcp
```

One-click editor installation:

| Client | Install |
|---|---|
| VS Code | [![Install on VS Code](https://img.shields.io/badge/Install_on_VS_Code-0098FF?style=flat-square&logo=visualstudiocode&logoColor=white)](https://vscode.dev/redirect/mcp/install?name=eu-climate&config=%7B%22type%22%3A%22stdio%22%2C%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22eea-climate-data-mcp%22%5D%7D) |
| Cursor | [![Install MCP Server](https://cursor.com/deeplink/mcp-install-light.svg)](https://cursor.com/en/install-mcp?name=eu-climate&config=eyJjb21tYW5kIjoidXZ4IiwiYXJncyI6WyJlZWEtY2xpbWF0ZS1kYXRhLW1jcCJdfQ==) |

## CLI examples

```bash
uv run eu-climate series emissions --country DE --sector total \
  --accounting-scope without_lulucf --start-year 1990

uv run eu-climate sectors search transport
uv run eu-climate series emissions --country HU --sector 1.A.3 --start-year 1990

uv run eu-climate measures list --country Hungary --status Implemented --sector Transport
uv run eu-climate measures get --country Hungary --measure-id 4

uv run eu-climate tables describe \
  --database GHG_Inventory --version latest --table ghg_value

uv run eu-climate values distinct \
  --database GHGPAMS --version latest \
  --table annexIX_flat_view_PaMs_elasticsearch --column Country

uv run eu-climate sql validate --query-file examples/country_inventory_counts.sql
uv run eu-climate sql run --query-file examples/country_inventory_counts.sql \
  --max-rows 100 --page-size 100
```

All execution paths use the same service and SQL guardrails. Queries must be one
parsed `SELECT`, fully qualify every table as `[database].[version].[table]`, use
allowlisted databases and versions, and remain within the requested bound. DDL, DML,
CTEs, `SELECT INTO`, system schemas, and unaliased computed columns are rejected.

## Verified source model

| Domain | Database | Country field | Live coverage | Status |
| --- | --- | --- | ---: | --- |
| National GHG inventory | `GHG_Inventory.latest` | `country_code` | 31 countries plus `EUA` | `reported_actual` |
| Policies and Measures | `GHGPAMS.latest` | `Country` | 30 countries | `reported_policy_estimate` |
| GHG projections | Not found in live metadata | — | — | Outside MVP |

Country identifiers differ between datasets: inventory uses codes such as `DE`, `FR`,
and `HU`, while Policies and Measures uses labels such as `Germany`, `France`, and
`Hungary`. Use metadata discovery or `values distinct` before constructing cross-domain
queries. `EUA` is an aggregate, not a country.

`latest` is mutable. Use a concrete version or revision for reproducible analysis when
the upstream exposes one. The latest inventory year is a published reporting year, not
a real-time emissions figure.

The `get_emissions_series` MCP tool and `series emissions` CLI command resolve the
appropriate inventory variable and sort results client-side because upstream rejects
`ORDER BY` on some `ghg_value` queries. `sector` accepts `total` or an IPCC sector
code at any depth (`1`, `1.A`, `1.A.3`); discover codes with
`search_emission_sectors`/`describe_emission_sector` (`sectors search|describe`).
Parent sectors already include their children — never sum a sector with its parent
or children.

The `list_measures`/`get_measure` tools (`measures list|get` CLI) expose the Policies
and Measures database as a searchable descriptive catalogue. Structured ex-ante and
ex-post effect values are sparse (several countries, including Hungary, report none),
so `get_measure` returns explicit quantification semantics — `reported` vs
`not_reported` — and missing values must not be read as zero impact. The catalogue is
deliberately not a ranking or impact-estimation source. Every result includes a query hash, retrieval
time, table references, reporting status, source links, and warnings.

Machine-readable output goes to stdout and diagnostics to stderr. Exit codes:

| Code | Meaning |
| ---: | --- |
| `0` | Success |
| `2` | Invalid or unsafe query/argument |
| `3` | Upstream unavailable or invalid response |
| `4` | Metadata object not found |

[docs/RECIPES.md](docs/RECIPES.md) contains six reproducible investigation
recipes (trend, sectoral change, road-transport contribution, PaMs reporting
completeness, sector quantification gaps, trend × measure stock) with exact
commands, formulas, query hashes, and caveats.

See [docs/SPIKE-REVIEW.md](docs/SPIKE-REVIEW.md) for evidence, limitations, and next
scope. The original Hungary-focused brief is retained as historical context in
[docs/SPIKE-hun-climate-policy-mcp.md](docs/SPIKE-hun-climate-policy-mcp.md).

## Development

```bash
uv run pytest
uv run ruff format --check src tests
uv run ruff check src tests
uv run mypy src tests
uv run python scripts/live_smoke.py
```

The live smoke suite is intentionally small and read-only.

## Release

Maintainers release from a clean, synchronized `main` branch:

```bash
scripts/release patch
```

The helper bumps the version, commits and pushes it, then creates a GitHub Release.
The release workflow builds the distributions and publishes them to PyPI through
trusted publishing.

## Configuration

| Variable | Default | Purpose |
| --- | --- | --- |
| `EEA_CLIMATE_DISCODATA_URL` | `https://discodata.eea.europa.eu` | Upstream service |
| `EEA_CLIMATE_TIMEOUT_SECONDS` | `30` | Request timeout, capped at 120 seconds |
| `EEA_CLIMATE_MAX_PAGE_SIZE` | `1000` | Local page-size ceiling |
