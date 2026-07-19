# hun-climate-policy-mcp

Schema-aware, read-only access to Hungarian climate data published through the
European Environment Agency's public Discodata service.

This MVP is a **conditional go**. It supports the verified GHG inventory and
Policies and Measures databases. A current projections database was not visible
in Discodata metadata during the 2026-07-19 spike, so WEM/WAM comparison is not
claimed.

> [!IMPORTANT]
> This is an independent, unofficial client. The EEA and the reporting countries
> remain the authoritative sources.

> [!WARNING]
> This repository is an experimental proof of concept, not a production service.
> Interfaces, upstream schemas, and the undocumented execution allowlist may change.
> See [`TODO.md`](TODO.md).

## Install

```bash
uv sync --extra test
uv run hun-climate databases list
uv run hun-climate-policy-mcp
```

The MCP command uses stdio transport. No credentials are required by the public
upstream service.

Claude Code:

```bash
claude mcp add --scope user hun-climate -- uvx hun-climate-policy-mcp
```

Codex CLI:

```bash
codex mcp add hun-climate -- uvx hun-climate-policy-mcp
```

## CLI examples

```bash
uv run hun-climate series emissions --country HU --sector total \
  --accounting-scope without_lulucf --start-year 1990

uv run hun-climate tables describe \
  --database GHG_Inventory --version latest --table ghg_value

uv run hun-climate values distinct \
  --database GHGPAMS --version latest \
  --table annexIX_flat_view_PaMs_elasticsearch --column Country

uv run hun-climate sql validate --query-file examples/hungary_inventory_counts.sql
uv run hun-climate sql run --query-file examples/hungary_inventory_counts.sql \
  --max-rows 100 --page-size 100
```

All execution paths use the same application service and SQL guardrails. Queries
must be one parsed `SELECT`, fully qualify every table as
`[database].[version].[table]`, use allowlisted climate databases/versions, and
remain within the requested bound. DDL, DML, CTEs, `SELECT INTO`, system schemas,
and unaliased computed columns are rejected.

## Verified source model

| Domain | Database | Hungary filter | Status |
| --- | --- | --- | --- |
| National GHG inventory | `GHG_Inventory.latest` | `country_code = 'HU'` (`HUN` also appears in metadata) | `reported_actual` |
| Policies and Measures | `GHGPAMS.latest` | `Country = 'Hungary'` | `reported_policy_estimate` |
| GHG projections | Not found in live metadata | — | Outside MVP |

`latest` is mutable. Use a concrete version/revision for reproducible analysis
where the upstream exposes one. The most recent inventory year (2024 at the
time of writing) is the latest published reporting year, not a real-time or
current-year emissions figure.

The `get_emissions_series` tool (CLI: `series emissions`) resolves the
statistically correct inventory variable — the plain `Total (with/without
LULUCF)` or sector aggregate, never the `TREND`/`BASE_YEAR_AVG`/
`PREV_SUBMISSION` variants — and sorts results client-side because upstream
rejects `ORDER BY` on `ghg_value`. Every query result includes the normalized query
hash, retrieval time, table references, reporting status, source links, and
warnings.

Machine-readable output goes to stdout and diagnostics to stderr. Exit codes are:

| Code | Meaning |
| ---: | --- |
| `0` | Success |
| `2` | Invalid or unsafe query/argument |
| `3` | Upstream unavailable or invalid response |
| `4` | Metadata object not found |

See [docs/SPIKE-REVIEW.md](docs/SPIKE-REVIEW.md) for the evidence, capability
matrix, limitations, and next scope.

## Development

```bash
uv run pytest
uv run ruff format --check src tests
uv run ruff check src tests
uv run mypy src tests
uv run python scripts/live_smoke.py
```

The live smoke suite is intentionally small and performs read-only calls.

## Configuration

| Variable | Default | Purpose |
| --- | --- | --- |
| `HUN_CLIMATE_DISCODATA_URL` | `https://discodata.eea.europa.eu` | Upstream service |
| `HUN_CLIMATE_TIMEOUT_SECONDS` | `30` | Request timeout, capped at 120 seconds |
| `HUN_CLIMATE_MAX_PAGE_SIZE` | `1000` | Local page-size ceiling |

