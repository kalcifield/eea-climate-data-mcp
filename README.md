# eu-climate-policy-mcp

Schema-aware, read-only access to European climate data published through the
European Environment Agency's public Discodata service.

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

```bash
uv sync --extra test
uv run eu-climate databases list
uv run eu-climate-policy-mcp
```

The MCP command uses stdio transport. No credentials are required.

Claude Code:

```bash
claude mcp add --scope user eu-climate -- uvx eu-climate-policy-mcp
```

Codex CLI:

```bash
codex mcp add eu-climate -- uvx eu-climate-policy-mcp
```

## CLI examples

```bash
uv run eu-climate series emissions --country DE --sector total \
  --accounting-scope without_lulucf --start-year 1990

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
`ORDER BY` on some `ghg_value` queries.

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

## Configuration

| Variable | Default | Purpose |
| --- | --- | --- |
| `EU_CLIMATE_DISCODATA_URL` | `https://discodata.eea.europa.eu` | Upstream service |
| `EU_CLIMATE_TIMEOUT_SECONDS` | `30` | Request timeout, capped at 120 seconds |
| `EU_CLIMATE_MAX_PAGE_SIZE` | `1000` | Local page-size ceiling |
