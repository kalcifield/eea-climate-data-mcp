from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Protocol, cast

from hun_climate_policy.config import Settings
from hun_climate_policy.discodata import DiscodataProvider
from hun_climate_policy.models import (
    Column,
    Provenance,
    QueryResult,
    SqlExplanation,
    TableDescription,
    ValidationResult,
    ReportingStatus,
)
from hun_climate_policy.errors import NotFoundError, UnsafeQueryError
from hun_climate_policy.profile import HUNGARY_PROFILE
from hun_climate_policy.sql_validation import SqlGuardrails

HELP_URL = "https://discodata.eea.europa.eu/Help.html"


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
        profile = HUNGARY_PROFILE["tables"].get(profile_key, {})
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
            HUNGARY_PROFILE["tables"]
            .get(".".join([*t.split(".")[:1], "latest", *t.split(".")[2:]]), {})
            .get("status", "unknown")
            for t in tables
        }
        return statuses.pop() if len(statuses) == 1 else "derived_by_tool"
