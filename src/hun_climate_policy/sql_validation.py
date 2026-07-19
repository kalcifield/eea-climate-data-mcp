from __future__ import annotations

from dataclasses import dataclass

from sqlglot import exp, parse
from sqlglot.errors import ParseError

from hun_climate_policy.config import Settings
from hun_climate_policy.models import SqlExplanation, ValidationResult


@dataclass(frozen=True)
class SqlGuardrails:
    settings: Settings

    def validate(self, sql: str, max_rows: int = 500) -> ValidationResult:
        errors: list[str] = []
        warnings: list[str] = []
        if not 1 <= max_rows <= 5000:
            return ValidationResult(valid=False, errors=["max_rows must be between 1 and 5000."])
        if not sql.strip():
            return ValidationResult(valid=False, errors=["SQL query is empty."])
        try:
            statements = [node for node in parse(sql, read="tsql") if node is not None]
        except ParseError as exc:
            return ValidationResult(valid=False, errors=[f"SQL parse error: {exc}"])
        if len(statements) != 1:
            return ValidationResult(valid=False, errors=["Exactly one SQL statement is required."])
        root = statements[0]
        if not isinstance(root, (exp.Select, exp.Union)):
            errors.append("Only SELECT queries are allowed.")
        forbidden_names = {
            "Insert",
            "Update",
            "Delete",
            "Create",
            "Drop",
            "Alter",
            "Merge",
            "Command",
            "Execute",
            "Transaction",
            "Grant",
            "Revoke",
            "Into",
        }
        for node in root.walk():
            if type(node).__name__ in forbidden_names:
                errors.append(f"Forbidden SQL construct: {type(node).__name__.upper()}.")
        if root.find(exp.With):
            errors.append("CTE/WITH is not supported by Discodata.")

        tables: list[str] = []
        for table in root.find_all(exp.Table):
            parts = [part.name for part in table.parts]
            rendered = ".".join(parts)
            tables.append(rendered)
            if len(parts) != 3:
                errors.append(
                    f"Table must be fully qualified as [database].[version].[table]: {rendered}."
                )
                continue
            database, version, _ = parts
            if database not in self.settings.allowed_databases:
                errors.append(f"Database is not allowlisted: {database}.")
            if version not in self.settings.allowed_versions:
                errors.append(f"Version is not allowlisted: {version}.")
            if database.lower() in {"master", "tempdb", "model", "msdb"} or version.lower() in {
                "sys",
                "information_schema",
            }:
                errors.append("System schemas and databases are forbidden.")

        for select in root.find_all(exp.Select):
            for projection in select.expressions:
                if not isinstance(projection, (exp.Column, exp.Star)) and not projection.alias:
                    errors.append(
                        f"Computed column requires an alias: {projection.sql(dialect='tsql')}."
                    )

        has_order_by = root.args.get("order") is not None or any(
            True for _ in root.find_all(exp.Order)
        )
        if not has_order_by:
            warnings.append("pagination requested without deterministic ORDER BY")
        else:
            warnings.append(
                "Live Discodata tests rejected ORDER BY for some inventory queries (error 10002)."
            )

        normalized = root.sql(dialect="tsql")
        bounded = normalized
        limit = root.args.get("limit")
        requested_limit: int | None = None
        if limit and isinstance(limit.expression, exp.Literal) and limit.expression.is_int:
            requested_limit = int(limit.expression.this)
            if requested_limit > max_rows:
                errors.append(f"SQL row limit {requested_limit} exceeds max_rows={max_rows}.")
        elif isinstance(root, exp.Select):
            bounded = root.copy().limit(max_rows).sql(dialect="tsql")
            requested_limit = max_rows
        else:
            warnings.append("UNION is page-bounded but no TOP limit was injected.")

        columns = sorted({column.sql(dialect="tsql") for column in root.find_all(exp.Column)})
        return ValidationResult(
            valid=not errors,
            normalized_sql=normalized,
            bounded_sql=bounded,
            errors=list(dict.fromkeys(errors)),
            warnings=list(dict.fromkeys(warnings)),
            tables=list(dict.fromkeys(tables)),
            columns=columns,
            has_order_by=has_order_by,
            row_limit=requested_limit,
        )

    def explain(self, sql: str, max_rows: int = 500) -> SqlExplanation:
        validation = self.validate(sql, max_rows)
        if not validation.normalized_sql:
            return SqlExplanation(validation=validation)
        root = parse(validation.normalized_sql, read="tsql")[0]
        assert root is not None
        tables = list(root.find_all(exp.Table))
        refs = [[part.name for part in table.parts] for table in tables]
        joins = list(root.find_all(exp.Join))
        aggregations = sorted(
            {type(node).__name__.upper() for node in root.walk() if isinstance(node, exp.AggFunc)}
        )
        filters = [node.this.sql(dialect="tsql") for node in root.find_all(exp.Where)]
        risks: list[str] = []
        if joins:
            risks.append(
                "Verify join cardinality against describe_table metadata; many-to-many joins can duplicate facts."
            )
        if not validation.has_order_by:
            risks.append("Pagination is not deterministic without ORDER BY on a stable key.")
        return SqlExplanation(
            validation=validation,
            databases=sorted({p[0] for p in refs if len(p) == 3}),
            versions=sorted({p[1] for p in refs if len(p) == 3}),
            tables=validation.tables,
            columns=validation.columns,
            joins=len(joins),
            aggregations=aggregations,
            filters=filters,
            risks=risks,
        )
