from __future__ import annotations

import json
from enum import Enum
from pathlib import Path
from typing import Any, Callable, TypeVar

import typer

from hun_climate_policy.errors import NotFoundError, UnsafeQueryError, UpstreamError
from hun_climate_policy.factory import create_service

T = TypeVar("T")


class OutputFormat(str, Enum):
    json = "json"
    jsonl = "jsonl"


app = typer.Typer(help="Read-only Hungarian climate data from EEA Discodata.", no_args_is_help=True)
databases_app = typer.Typer(no_args_is_help=True)
tables_app = typer.Typer(no_args_is_help=True)
values_app = typer.Typer(no_args_is_help=True)
sql_app = typer.Typer(no_args_is_help=True)
series_app = typer.Typer(no_args_is_help=True)
app.add_typer(databases_app, name="databases")
app.add_typer(tables_app, name="tables")
app.add_typer(values_app, name="values")
app.add_typer(sql_app, name="sql")
app.add_typer(series_app, name="series")


def run(operation: Callable[[], T]) -> T:
    try:
        return operation()
    except NotFoundError as exc:
        typer.echo(f"not found: {exc}", err=True)
        raise typer.Exit(4) from exc
    except UpstreamError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(3) from exc
    except (UnsafeQueryError, ValueError) as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(2) from exc


def emit(value: Any, fmt: OutputFormat = OutputFormat.json) -> None:
    if hasattr(value, "model_dump"):
        value = value.model_dump(mode="json")
    if fmt == OutputFormat.jsonl:
        envelope = (
            value if isinstance(value, dict) and isinstance(value.get("results"), list) else None
        )
        rows = value.get("results", value) if isinstance(value, dict) else value
        if not isinstance(rows, list):
            rows = [rows]
        for row in rows:
            typer.echo(json.dumps(row, ensure_ascii=False, default=str))
        if envelope is not None:
            metadata = {key: item for key, item in envelope.items() if key != "results"}
            typer.echo(json.dumps({"_meta": metadata}, ensure_ascii=False, default=str))
    else:
        typer.echo(json.dumps(value, ensure_ascii=False, indent=2, default=str))


def read_query(query_file: Path) -> str:
    return query_file.read_text(encoding="utf-8")


@databases_app.command("list")
def databases_list(no_cache: bool = False, format: OutputFormat = OutputFormat.json) -> None:
    emit(run(lambda: create_service().list_databases(no_cache)), format)


@databases_app.command("versions")
def database_versions(
    database: str, no_cache: bool = False, format: OutputFormat = OutputFormat.json
) -> None:
    emit(run(lambda: create_service().list_versions(database, no_cache)), format)


@tables_app.command("list")
def tables_list(
    database: str,
    version: str = "latest",
    no_cache: bool = False,
    format: OutputFormat = OutputFormat.json,
) -> None:
    emit(run(lambda: create_service().list_tables(database, version, no_cache)), format)


@tables_app.command("search")
def tables_search(
    text: str, no_cache: bool = False, format: OutputFormat = OutputFormat.json
) -> None:
    emit(run(lambda: create_service().search_tables(text, no_cache)), format)


@tables_app.command("describe")
def tables_describe(
    database: str = typer.Option(...),
    version: str = typer.Option("latest"),
    table: str = typer.Option(...),
    no_cache: bool = False,
    format: OutputFormat = OutputFormat.json,
) -> None:
    emit(run(lambda: create_service().describe_table(database, version, table, no_cache)), format)


@tables_app.command("preview")
def tables_preview(
    database: str = typer.Option(...),
    version: str = typer.Option("latest"),
    table: str = typer.Option(...),
    max_rows: int = 5,
    format: OutputFormat = OutputFormat.json,
) -> None:
    emit(run(lambda: create_service().preview_rows(database, version, table, max_rows)), format)


@values_app.command("distinct")
def values_distinct(
    database: str = typer.Option(...),
    version: str = typer.Option("latest"),
    table: str = typer.Option(...),
    column: str = typer.Option(...),
    max_rows: int = 100,
    format: OutputFormat = OutputFormat.json,
) -> None:
    emit(
        run(
            lambda: create_service().list_distinct_values(
                database, version, table, column, max_rows
            )
        ),
        format,
    )


@sql_app.command("validate")
def sql_validate(
    query_file: Path = typer.Option(..., exists=True, readable=True), max_rows: int = 500
) -> None:
    result = create_service().validate_sql(read_query(query_file), max_rows)
    emit(result)
    if not result.valid:
        raise typer.Exit(2)


@sql_app.command("explain")
def sql_explain(
    query_file: Path = typer.Option(..., exists=True, readable=True), max_rows: int = 500
) -> None:
    emit(run(lambda: create_service().explain_sql(read_query(query_file), max_rows)))


@sql_app.command("run")
def sql_run(
    query_file: Path = typer.Option(..., exists=True, readable=True),
    format: OutputFormat = OutputFormat.json,
    max_rows: int = 500,
    page: int = 1,
    page_size: int = 100,
    timeout: float = 30.0,
    explain: bool = False,
) -> None:
    query = read_query(query_file)
    svc = create_service()
    if explain:
        emit(svc.explain_sql(query, max_rows), format)
        return
    emit(
        run(
            lambda: svc.query_sql(
                query, max_rows=max_rows, page=page, page_size=page_size, timeout=timeout
            )
        ),
        format,
    )


@series_app.command("emissions")
def series_emissions(
    country: str = typer.Option(...),
    sector: str = "total",
    gas: str = "Aggregate GHGs",
    accounting_scope: str = "without_lulucf",
    start_year: int | None = None,
    end_year: int | None = None,
    format: OutputFormat = OutputFormat.json,
) -> None:
    emit(
        run(
            lambda: create_service().get_emissions_series(
                country, sector, gas, accounting_scope, start_year, end_year
            )
        ),
        format,
    )


@sql_app.command("capabilities")
def sql_capabilities() -> None:
    emit(create_service().get_sql_capabilities())


def main() -> None:
    app()


if __name__ == "__main__":
    main()
