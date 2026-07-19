# SPIKE review — EEA Discodata for European climate policy

Checked: 2026-07-19

## Decision: CONDITIONAL GO

The public API, machine-readable schema metadata, European GHG inventory data,
and national Policies and Measures records are sufficient for a useful guarded
vertical slice. The service needs no authentication and returns JSON.

The full product is not yet a GO: no dedicated current GHG projections dataset
was visible in the live metadata, policy impact fields are materially sparse,
and valid T-SQL can still be rejected by an undocumented upstream execution
allowlist. The MVP therefore makes no WEM/WAM or 2030 target-progress claims.

## Live findings

- `GET /md` returned roughly 24 MB of database/version/table/column metadata.
- `GET /sql?query=...&p=1&nrOfHits=100` is public and paginated; documented
  default page size is 100. No documented maximum page size or SLA was found.
- `latest` points to the newest version and revision. A `vN` alias points to the
  newest revision in that major version; explicit `vNrN` revisions also exist.
- `GHG_Inventory.latest` exposes `ghg_meta`, `ghg_value`, `ghg_variable`, and
  `ghg_unit_conversion`.
- Live inventory values covered 31 countries plus the `EUA` aggregate. Country codes
  include `HU`; `HUN` also appears in metadata.
- `GHGPAMS.latest` exposes the 181-column
  `annexIX_flat_view_PaMs_elasticsearch` with 30 country labels. Country identifiers
  are names such as `Hungary`, not inventory codes such as `HU`.
- Current policy records include implementation status and 2030-effect fields, but
  sampled 2030 total-effect values were null.
- Inventory joins on `ghg_value.variable_uid = ghg_variable.variable_uid`
  executed successfully.

## Capability matrix

| Construct | Result | Evidence/handling |
| --- | --- | --- |
| `SELECT`, `WHERE` | Supported | Live inventory and PaM queries |
| `JOIN` | Supported | Live inventory variable join |
| `GROUP BY`, aggregate alias | Supported | Live yearly `COUNT(*) AS n` |
| `DISTINCT`, `TOP`, `LIKE` | Supported | Live country/value probes |
| `ORDER BY` | Conditional | Inventory probes returned error `10002` |
| CTE / `WITH` | Unsupported | Explicitly documented by Discodata |
| DDL | Forbidden | Explicitly documented; also blocked locally |
| Computed/aggregate without alias | Unsupported | Documented JSON key constraint |
| `HAVING`, `CASE`, `IN`, `BETWEEN`, subqueries, `UNION`, windows, `PIVOT` | Unverified | Parser accepts where safe; upstream may reject |
| Cross-database join | Unverified | Locally allowlisted only across the two climate DBs |
| Multiple statements | Rejected locally | One parsed statement required |

`ORDER BY` is still recommended for stable pagination, but upstream acceptance
depends on query shape. The tool warns both when it is absent and about the live
rejection observed when it is present.

## Grain and joins

| Table | Grain | Logical key | Join |
| --- | --- | --- | --- |
| `GHG_Inventory.latest.ghg_meta` | country × submission | `country_code`, `submission_version` | identifies reporting cycle |
| `GHG_Inventory.latest.ghg_value` | country × submission × inventory year × variable | `country_code`, `submission_version`, `inventory_year`, `variable_uid` | many-to-one to `ghg_variable` |
| `GHG_Inventory.latest.ghg_variable` | inventory variable | `variable_uid` | describes gas, sector, measure, unit |
| `GHGPAMS.latest.annexIX_flat_view_PaMs_elasticsearch` | flat reported policy/measure record | `Country`, `Report_ID`, `ID_of_policy_or_measure` | no cross-domain join claimed |

The logical keys are application profile assertions based on the schema and
live samples, not declared upstream constraints. Agents must not sum across
variables without filtering measure, gas, unit, and sector hierarchy.

## Guardrail design

- Parse with SQLGlot's T-SQL dialect; do not authorize with regex alone.
- Require exactly one `SELECT`/`UNION` tree and fully-qualified table names.
- Reject DML, DDL, commands, execution, transactions, `SELECT INTO`, CTEs, and
  system objects.
- Allowlist `GHG_Inventory` and `GHGPAMS`, plus known live version names.
- Enforce `max_rows`, `page_size <= 1000`, `timeout <= 120s`; inject `TOP` into
  simple unbounded selects.
- Require aliases on calculated and aggregate projections.
- Warn about missing deterministic order, joins, cross-domain provenance, and
  known upstream `ORDER BY` instability.
- Do not cache query results in the MVP. Metadata is cached for 24 hours; errors
  are not cached.

## Provenance and reporting status

Inventory observations map to `reported_actual`, with the important row-level
exception `isCalculatedByEEA=1`. PaM quantified impact fields map to
`reported_policy_estimate`. Projection status is defined but intentionally not
assigned because the relevant upstream dataset was not found. Any result that
combines reporting domains maps to `derived_by_tool`.

## Risks

1. `latest` changes and can alter results without a client release.
2. Upstream has no published SLA, maximum page size, cancellation endpoint, or
   complete SQL allowlist.
3. Pagination without a stable order can repeat or omit rows; ordered queries
   may themselves be rejected for some shapes.
4. Metadata descriptions are uneven and do not declare primary/foreign keys.
5. Flat PaM records and null estimates require careful semantic interpretation.
6. The upstream query URL contains SQL; logs should avoid storing raw queries
   with sensitive literals even though these datasets are public.

## Next MVP scope

Keep this vertical slice until an official projections source is identified.
Next, record a broader capability fixture, quantify PaM completeness by country,
report, and status, add cancellation at the adapter boundary, and pin profile
metadata to explicit revisions. Only then add `compare_scenarios` or
`assess_target_progress`.

## Primary sources

- EEA Discodata help: <https://discodata.eea.europa.eu/Help.html>
- EEA data hub: <https://www.eea.europa.eu/en/datahub>
- Governance Regulation: <https://eur-lex.europa.eu/eli/reg/2018/1999/oj>
- UNFCCC reporting guidance: <https://unfccc.int/ghg-inventories-annex-i-parties/2024>
- IPCC 2006 Guidelines: <https://www.ipcc-nggip.iges.or.jp/public/2006gl/>
