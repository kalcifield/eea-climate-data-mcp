# Repository Guidelines

## Project Structure

Python uses the `src` layout under `src/eea_climate_data/`. Keep typed data contracts
in `models.py`, workflows in `service.py`, SQL safety in `sql_validation.py`, upstream
wire behavior in `discodata.py`, and verified EEA table semantics in `profile.py`. Keep
`cli.py` and `mcp_server.py` thin; both must call the same `ClimatePolicyService`
methods. Design findings and live evidence belong in `docs/`.

## Development Commands

Use Python 3.11+ and `uv`:

```bash
uv sync --extra test
uv run eu-climate --help
uv run eea-climate-data-mcp
uv run pytest -q
uv run ruff format --check src tests
uv run ruff check src tests
uv run mypy src tests
```

Release with `scripts/release {patch|minor|major}`. GitHub Actions publishes to PyPI
through the `pypi` environment after the GitHub Release is created.

Run `uv run python scripts/live_smoke.py` only when explicitly validating the public
service. Keep live probes small, bounded, read-only, and separate from routine tests.

## Code and Interface Conventions

Use type annotations and Pydantic models at public boundaries. Modules, functions, and
variables use `snake_case`; classes and models use `PascalCase`. Preserve upstream field
names in provider payloads and normalized semantics in domain models. Machine-readable
output goes to stdout; diagnostics go to stderr. JSON and JSONL output must remain
semantically equivalent. Avoid provider logic in CLI or MCP adapters.

## SQL Safety

Never weaken the single-statement, `SELECT`-only, database/version allowlist,
fully-qualified-table, row-bound, page-size, timeout, computed-alias, or system-schema
guardrails. Continue using a T-SQL parser; regex alone must not authorize queries. Block
DDL, DML, execution, transactions, `SELECT INTO`, CTEs, and unsupported system objects.
Warn when pagination lacks deterministic ordering. Do not log raw SQL containing user
literals. Query results are deliberately not cached unless a reviewed design changes
that policy.

## Provenance and Climate Semantics

Every executed query returns provider, database/version, table references, normalized
query hash, retrieval time, source links, warnings, and reporting status. Preserve the
distinction between `reported_actual`, `reported_projection`,
`reported_policy_estimate`, and `derived_by_tool`. Null policy estimates never mean
zero. Do not infer causality, target progress, or WEM/WAM results without verified data.
Treat `latest` as mutable, and do not apply profile grain or join claims to another
revision without checking its schema.

## Testing

Routine tests use deterministic fixtures and mocked HTTP responses; they must not need
network access. Name tests `test_<behavior>`. Cover SQL classification and bounds,
allowlists, error mapping, schema drift, pagination, provenance, reporting status, and
CLI/MCP parity. Add a regression test for every guardrail or upstream-contract bug.
Live tests prove current compatibility but do not replace deterministic contract tests.

## Upstream Etiquette and Changes

The EEA service is public but has no guaranteed SLA. Use explicit timeouts, bounded page
sizes, metadata caching, and no crawling or load testing. Errors must not enter the
metadata cache. New dependencies require a quick maintenance and adoption check. Keep
changes small and update `CHANGELOG.md` for user-visible behavior when that file exists.
Use Conventional Commit prefixes: `feat`, `fix`, `refactor`, `build`, `ci`, `chore`,
`docs`, `style`, `perf`, or `test`.
