from __future__ import annotations

import re
from datetime import UTC, datetime
from typing import Any, Protocol, cast

from eu_climate_policy.config import Settings
from eu_climate_policy.discodata import DiscodataProvider
from eu_climate_policy.models import (
    Column,
    EmissionsSeriesResult,
    Provenance,
    QueryResult,
    SqlExplanation,
    TableDescription,
    ValidationResult,
    ReportingStatus,
)
from eu_climate_policy.errors import NotFoundError, UnsafeQueryError
from eu_climate_policy.profile import EEA_CLIMATE_PROFILE
from eu_climate_policy.sql_validation import SqlGuardrails

HELP_URL = "https://discodata.eea.europa.eu/Help.html"
PAMS_TABLE = "[GHGPAMS].[latest].[annexIX_flat_view_PaMs_elasticsearch]"
PAMS_EXANTE_YEARS = (2025, 2030, 2035, 2040, 2045, 2050, 2055)
PAMS_EXANTE_COLUMNS = {
    "total": "Total_GHG_emissions_reductions_in_{year}__kt_CO2eq_y_GHG",
    "esr": "GHG_emissions_reductions_ESR_in_{year}__kt_CO2eq_y_GHG",
    "eu_ets": "GHG_emissions_reductions_EU_ETS_in_{year}__kt_CO2eq_y_GHG",
    "lulucf": "GHG_emissions_reductions_LULUCF_in_{year}__kt_CO2eq_y_GHG",
}
QUANTIFICATION_CAVEAT = (
    "Structured ex-ante/ex-post effect values are sparse in PaMs reporting; "
    "missing values mean 'not reported', not zero impact."
)


class DiscodataClient(Protocol):
    def metadata(self, no_cache: bool = False) -> list[dict[str, Any]]: ...

    def query(
        self, sql: str, page: int, page_size: int, timeout: float | None = None
    ) -> list[dict[str, Any]]: ...

    @staticmethod
    def query_hash(sql: str) -> str: ...


class ClimatePolicyService:
    def __init__(
        self, provider: DiscodataClient | None = None, settings: Settings | None = None
    ) -> None:
        self.settings = settings or Settings()
        self.provider = provider or DiscodataProvider(self.settings)
        self.guardrails = SqlGuardrails(self.settings)

    def _allowed_metadata(self, no_cache: bool = False) -> list[dict[str, Any]]:
        return [
            d
            for d in self.provider.metadata(no_cache)
            if d.get("database") in self.settings.allowed_databases
        ]

    def list_databases(self, no_cache: bool = False) -> list[dict[str, Any]]:
        result = []
        for db in self._allowed_metadata(no_cache):
            versions = [s["name"] for s in db.get("Schemas", [])]
            result.append(
                {
                    "database": db["database"],
                    "versions": versions,
                    "latest_available": "latest" in versions,
                }
            )
        return result

    def list_versions(self, database: str, no_cache: bool = False) -> list[str]:
        db = self._database(database, no_cache)
        return [s["name"] for s in db.get("Schemas", [])]

    def list_tables(
        self, database: str, version: str = "latest", no_cache: bool = False
    ) -> list[dict[str, Any]]:
        schema = self._schema(database, version, no_cache)
        return [
            {
                "table": t["name"],
                "table_type": t.get("tableType"),
                "columns": len(t.get("Columns", [])),
            }
            for t in schema.get("Tables", [])
        ]

    def search_tables(self, text: str, no_cache: bool = False) -> list[dict[str, str]]:
        needle = text.casefold()
        hits = []
        for db in self._allowed_metadata(no_cache):
            schema = next((s for s in db.get("Schemas", []) if s.get("name") == "latest"), None)
            for table in (schema or {}).get("Tables", []):
                haystack = " ".join(
                    [table.get("name", ""), table.get("description", "")]
                ).casefold()
                column_match = any(
                    needle in (c.get("name", "") + " " + c.get("description", "")).casefold()
                    for c in table.get("Columns", [])
                )
                if needle in haystack or column_match:
                    hits.append(
                        {"database": db["database"], "version": "latest", "table": table["name"]}
                    )
        return hits

    def describe_table(
        self, database: str, version: str, table: str, no_cache: bool = False
    ) -> TableDescription:
        schema = self._schema(database, version, no_cache)
        raw = next((t for t in schema.get("Tables", []) if t.get("name") == table), None)
        if raw is None:
            raise NotFoundError(f"Unknown table: {database}.{version}.{table}")
        profile_key = f"{database}.latest.{table}"
        profile = EEA_CLIMATE_PROFILE["tables"].get(profile_key, {})
        return TableDescription(
            database=database,
            version=version,
            table=table,
            table_type=raw.get("tableType"),
            description=raw.get("description"),
            grain=profile.get("grain"),
            logical_key=profile.get("logical_key", []),
            reporting_cycle=profile.get("reporting_cycle"),
            columns=[
                Column(
                    name=c["name"],
                    data_type=c.get("dataType", "unknown"),
                    description=c.get("description"),
                )
                for c in raw.get("Columns", [])
            ],
            joins=profile.get("joins", []),
            caveats=profile.get("caveats", []),
            source_links=[HELP_URL],
        )

    def validate_sql(self, sql: str, max_rows: int = 500) -> ValidationResult:
        return self.guardrails.validate(sql, max_rows)

    def explain_sql(self, sql: str, max_rows: int = 500) -> SqlExplanation:
        return self.guardrails.explain(sql, max_rows)

    def query_sql(
        self,
        sql: str,
        *,
        max_rows: int = 500,
        page: int = 1,
        page_size: int = 100,
        timeout: float | None = None,
    ) -> QueryResult:
        if page < 1:
            raise ValueError("page must be >= 1")
        if timeout is not None and not 1 <= timeout <= 120:
            raise ValueError("timeout must be between 1 and 120 seconds")
        if not 1 <= page_size <= min(max_rows, self.settings.max_page_size):
            raise ValueError(
                f"page_size must be between 1 and {min(max_rows, self.settings.max_page_size)}"
            )
        validation = self.validate_sql(sql, max_rows)
        if not validation.valid:
            raise UnsafeQueryError("; ".join(validation.errors))
        bounded_sql = validation.bounded_sql or sql
        rows = self.provider.query(
            bounded_sql, page, page_size, timeout or self.settings.timeout_seconds
        )
        refs = [table.split(".") for table in validation.tables]
        database = refs[0][0] if refs and len(refs[0]) == 3 else None
        version = refs[0][1] if refs and len(refs[0]) == 3 else None
        status = self._reporting_status(validation.tables)
        warnings = list(validation.warnings)
        if len({r[0] for r in refs if len(r) == 3}) > 1:
            warnings.append(
                "Cross-database query combines reporting domains; inspect provenance per table."
            )
            status = "derived_by_tool"
        return QueryResult(
            results=rows,
            page=page,
            page_size=page_size,
            returned_rows=len(rows),
            has_more=len(rows) == page_size,
            provenance=Provenance(
                database=database,
                version=version,
                tables=validation.tables,
                query_hash=self.provider.query_hash(bounded_sql),
                retrieved_at=datetime.now(UTC),
                reporting_status=status,
                source_links=[HELP_URL, f"{self.settings.base_url}/sql"],
                warnings=warnings,
            ),
        )

    def preview_rows(
        self, database: str, version: str, table: str, max_rows: int = 5
    ) -> QueryResult:
        sql = f"SELECT TOP {max_rows} * FROM [{database}].[{version}].[{table}]"
        return self.query_sql(sql, max_rows=max_rows, page_size=max_rows)

    def list_distinct_values(
        self, database: str, version: str, table: str, column: str, max_rows: int = 100
    ) -> QueryResult:
        description = self.describe_table(database, version, table)
        if column not in {c.name for c in description.columns}:
            raise NotFoundError(f"Unknown column: {column}")
        sql = f"SELECT DISTINCT TOP {max_rows} [{column}] FROM [{database}].[{version}].[{table}]"
        return self.query_sql(sql, max_rows=max_rows, page_size=max_rows)

    def search_emission_sectors(self, query: str, max_rows: int = 50) -> dict[str, Any]:
        escaped = query.replace("'", "''")
        sql = (
            "SELECT DISTINCT r.sector_number, r.navigation, r.sector "
            "FROM [GHG_Inventory].[latest].[ghg_variable] AS r "
            f"WHERE (r.sector_number LIKE '{escaped}%' OR r.navigation LIKE '%{escaped}%') "
            "AND r.sector_number IS NOT NULL"
        )
        result = self.query_sql(sql, max_rows=500, page_size=500)
        by_code: dict[str, dict[str, Any]] = {}
        for row in result.results:
            code = str(row.get("sector_number") or "").strip()
            if not code or code == "Sectors/Totals":
                continue
            navigation = str(row.get("navigation") or "")
            entry = by_code.setdefault(
                code,
                {
                    "sector_code": code,
                    "name": navigation,
                    "ipcc_sector": row.get("sector"),
                    "level": len(code.split(".")),
                    "parent": ".".join(code.split(".")[:-1]) or None,
                },
            )
            # prefer the navigation label that spells out the code itself
            if navigation.startswith(f"{code}."):
                entry["name"] = navigation
        sectors = sorted(by_code.values(), key=lambda e: str(e["sector_code"]))[:max_rows]
        return {
            "query": query,
            "sectors": sectors,
            "provenance": result.provenance.model_dump(mode="json"),
        }

    def describe_emission_sector(self, sector_code: str) -> dict[str, Any]:
        code = sector_code.strip()
        found = self.search_emission_sectors(code, max_rows=500)
        entries = {e["sector_code"]: e for e in found["sectors"]}
        entry = entries.get(code)
        if entry is None:
            raise NotFoundError(f"Unknown emission sector code: {code}")
        depth = len(code.split("."))
        children = sorted(
            c for c in entries if c.startswith(f"{code}.") and len(c.split(".")) == depth + 1
        )
        return {
            **entry,
            "children": children,
            "caveats": [
                "Parent sectors already include their children; never sum a sector "
                "with its parent or children (double counting)."
            ],
            "provenance": found["provenance"],
        }

    def get_emissions_series(
        self,
        country: str,
        sector: str = "total",
        gas: str = "Aggregate GHGs",
        accounting_scope: str = "without_lulucf",
        start_year: int | None = None,
        end_year: int | None = None,
    ) -> EmissionsSeriesResult:
        scope_parameter = {
            "with_lulucf": "Total (with LULUCF)",
            "without_lulucf": "Total (without LULUCF)",
        }.get(accounting_scope)
        if scope_parameter is None:
            raise ValueError("accounting_scope must be 'with_lulucf' or 'without_lulucf'")
        sector_key = sector.strip()
        if sector_key.lower() == "total":
            sector_key = "total"
        elif not re.fullmatch(r"\d(\.[\w()]+)*", sector_key):
            raise ValueError(
                "sector must be 'total' or an IPCC sector code such as '1', '1.A', '1.A.3'"
            )

        def quoted(text: str) -> str:
            return "'" + text.replace("'", "''") + "'"

        parameter = scope_parameter if sector_key == "total" else "no parameter"
        sector_number = "Sectors/Totals" if sector_key == "total" else sector_key
        variable_sql = (
            "SELECT r.variable_uid, r.variable_name, r.unit, r.classification, r.navigation, "
            "r.is_template, r.is_country_specific "
            "FROM [GHG_Inventory].[latest].[ghg_variable] AS r "
            f"WHERE r.sector_number = {quoted(sector_number)} AND r.gas = {quoted(gas)} "
            f"AND r.measure = 'Emissions' AND r.parameter = {quoted(parameter)}"
        )
        candidates = self.query_sql(variable_sql, max_rows=50, page_size=50).results
        if sector_key != "total":
            # plain sector aggregate only: skip memo items, templates, and HWP approach
            # variants; no classification filter because subsectors carry their own
            # classification labels (e.g. 'Fuels' on 1.A.3)
            candidates = [
                c
                for c in candidates
                if not c.get("is_template")
                and not c.get("is_country_specific")
                and str(c.get("navigation", "")).startswith(f"{sector_key}.")
            ]
        preferred = [c for c in candidates if c.get("unit") == "kt CO₂ equivalent"] or candidates
        if not preferred:
            raise NotFoundError(
                f"No inventory variable matches sector={sector}, gas={gas}, "
                f"accounting_scope={accounting_scope}"
            )
        if len(preferred) > 1:
            names = "; ".join(str(c.get("variable_name")) for c in preferred)
            raise NotFoundError(
                f"Ambiguous inventory variable match, refine via query_sql: {names}"
            )
        variable = preferred[0]

        filters = [
            f"v.country_code = {quoted(country)}",
            f"v.variable_uid = {quoted(str(variable['variable_uid']))}",
        ]
        if start_year is not None:
            filters.append(f"v.inventory_year >= {int(start_year)}")
        if end_year is not None:
            filters.append(f"v.inventory_year <= {int(end_year)}")
        # no ORDER BY on purpose: upstream rejects it on ghg_value (error 10002); sorted locally
        value_sql = (
            "SELECT v.inventory_year, v.value FROM [GHG_Inventory].[latest].[ghg_value] AS v "
            "WHERE " + " AND ".join(filters)
        )
        result = self.query_sql(value_sql, max_rows=500, page_size=500)
        series = sorted(
            (
                {"year": int(r["inventory_year"]), "value": float(r["value"])}
                for r in result.results
                if r.get("value") is not None
            ),
            key=lambda point: point["year"],
        )
        provenance = result.provenance
        provenance.warnings = [
            *provenance.warnings,
            "Upstream ordering was not used; results were sorted client-side.",
        ]
        if sector_key != "total":
            provenance.warnings.append(
                "accounting_scope applies only to sector='total'; "
                "sector series are the reported sector aggregates."
            )
            provenance.warnings.append(
                f"Values cover sector {sector_key} only; do not sum with parent or "
                "child sector series (double counting)."
            )
        return EmissionsSeriesResult(
            country=country,
            sector=sector,
            gas=gas,
            accounting_scope=accounting_scope,
            unit=variable.get("unit"),
            variable_uid=str(variable["variable_uid"]),
            variable_name=variable.get("variable_name"),
            series=series,
            provenance=provenance,
        )

    def list_measures(
        self,
        country: str | None = None,
        status: str | None = None,
        sector: str | None = None,
        instrument_type: str | None = None,
        start_year: int | None = None,
        necp_reference: str | None = None,
        responsible_entity: str | None = None,
        free_text: str | None = None,
        max_rows: int = 100,
    ) -> QueryResult:
        def quoted(text: str) -> str:
            return "'" + text.replace("'", "''") + "'"

        def contains(column: str, text: str) -> str:
            return f"{column} LIKE '%{text.replace(chr(39), chr(39) * 2)}%'"

        filters = []
        if country:
            filters.append(f"p.Country = {quoted(country)}")
        if status:
            filters.append(f"p.Status_of_implementation = {quoted(status)}")
        if sector:
            filters.append(contains("p.Sector_s__affected", sector))
        if instrument_type:
            filters.append(contains("p.Type_of_policy_instrument", instrument_type))
        if start_year is not None:
            filters.append(f"p.Implementation_period_start = {quoted(str(int(start_year)))}")
        if necp_reference:
            filters.append(f"p.PaM_number_in_NECP = {quoted(necp_reference)}")
        if responsible_entity:
            filters.append(
                contains("p.Entities_responsible_for_implementing_the_policy", responsible_entity)
            )
        if free_text:
            filters.append(
                "("
                + " OR ".join(
                    contains(column, free_text)
                    for column in (
                        "p.Name_of_policy_or_measure",
                        "p.Description",
                        "p.Objective_s_",
                    )
                )
                + ")"
            )
        sql = (
            "SELECT p.Country, p.ID_of_policy_or_measure, p.Name_of_policy_or_measure, "
            "p.Status_of_implementation, p.Sector_s__affected, p.Type_of_policy_instrument, "
            "p.Implementation_period_start, p.PaM_number_in_NECP "
            f"FROM {PAMS_TABLE} AS p"
        )
        if filters:
            sql += " WHERE " + " AND ".join(filters)
        result = self.query_sql(sql, max_rows=max_rows, page_size=min(max_rows, 500))
        result.provenance.warnings.append(QUANTIFICATION_CAVEAT)
        return result

    def get_measure(self, country: str, measure_id: int) -> dict[str, Any]:
        country_sql = "'" + country.replace("'", "''") + "'"
        sql = (
            f"SELECT * FROM {PAMS_TABLE} AS p "
            f"WHERE p.Country = {country_sql} AND p.ID_of_policy_or_measure = {int(measure_id)}"
        )
        result = self.query_sql(sql, max_rows=2, page_size=2)
        if not result.results:
            raise NotFoundError(f"No measure {measure_id} for country {country}")
        row = result.results[0]

        def numeric(value: Any) -> float | None:
            try:
                return None if value is None else float(value)
            except (TypeError, ValueError):
                return None

        ex_ante: dict[str, dict[int, float]] = {}
        for scope, pattern in PAMS_EXANTE_COLUMNS.items():
            values = {
                year: v
                for year in PAMS_EXANTE_YEARS
                if (v := numeric(row.get(pattern.format(year=year)))) is not None
            }
            if values:
                ex_ante[scope] = values
        ex_post_value = numeric(row.get("Average_expost_emission_reduction__kt_CO2eq_y_GHG"))
        ex_post = (
            {
                "average_kt_co2eq_per_year": ex_post_value,
                "applies_to_year": row.get("Year_for_which_reduction_applies__expost_GHG"),
            }
            if ex_post_value is not None
            else None
        )
        reported = bool(ex_ante) or ex_post is not None
        quantification: dict[str, Any] = {
            "quantification_available": reported,
            "quantification_status": "reported" if reported else "not_reported",
            "ex_ante_kt_co2eq_per_year": ex_ante,
            "ex_post": ex_post,
        }
        if not reported:
            quantification["warning"] = QUANTIFICATION_CAVEAT
        return {
            "measure": row,
            "quantification": quantification,
            "provenance": result.provenance.model_dump(mode="json"),
        }

    def get_sql_capabilities(self) -> dict[str, Any]:
        return {
            "dialect": "T-SQL subset",
            "live_checked_at": "2026-07-19",
            "capabilities": {
                "select": "supported",
                "where": "supported",
                "join": "supported",
                "group_by": "supported",
                "distinct": "supported",
                "top": "supported",
                "order_by": "conditional",
                "cte_with": "unsupported_documented",
                "ddl": "forbidden",
                "multiple_statements": "forbidden_local",
                "computed_column_without_alias": "unsupported_documented",
            },
            "notes": [
                "ORDER BY returned Discodata error 10002 in live GHG inventory tests; retry only after removing it or changing query shape."
            ],
            "source": HELP_URL,
        }

    def get_provenance(self, sql: str, max_rows: int = 500) -> dict[str, Any]:
        validation = self.validate_sql(sql, max_rows)
        return {
            "provider": "EEA Discodata",
            "tables": validation.tables,
            "reporting_status": self._reporting_status(validation.tables),
            "source_links": [HELP_URL],
            "validation": validation.model_dump(mode="json"),
        }

    def describe_reporting_status(self) -> dict[str, str]:
        return {
            "reported_actual": "Member-state inventory observation (unless isCalculatedByEEA=1).",
            "reported_projection": "Member-state reported scenario projection; not available in the verified MVP databases.",
            "reported_policy_estimate": "Reported ex-ante or ex-post policy/measure effect estimate.",
            "derived_by_tool": "Calculated or combined by this tool; not a directly reported value.",
        }

    def _database(self, name: str, no_cache: bool = False) -> dict[str, Any]:
        if name not in self.settings.allowed_databases:
            raise UnsafeQueryError(f"Database is not allowlisted: {name}")
        db = next((d for d in self._allowed_metadata(no_cache) if d.get("database") == name), None)
        if db is None:
            raise NotFoundError(f"Database unavailable: {name}")
        return db

    def _schema(self, database: str, version: str, no_cache: bool = False) -> dict[str, Any]:
        if version not in self.settings.allowed_versions:
            raise UnsafeQueryError(f"Version is not allowlisted: {version}")
        db = self._database(database, no_cache)
        schema = next((s for s in db.get("Schemas", []) if s.get("name") == version), None)
        if schema is None:
            raise NotFoundError(f"Unknown version: {database}.{version}")
        return cast(dict[str, Any], schema)

    @staticmethod
    def _reporting_status(tables: list[str]) -> ReportingStatus:
        statuses = {
            EEA_CLIMATE_PROFILE["tables"]
            .get(".".join([*t.split(".")[:1], "latest", *t.split(".")[2:]]), {})
            .get("status", "unknown")
            for t in tables
        }
        return statuses.pop() if len(statuses) == 1 else "derived_by_tool"
