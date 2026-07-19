from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

ReportingStatus = Literal[
    "reported_actual",
    "reported_projection",
    "reported_policy_estimate",
    "derived_by_tool",
    "unknown",
]


class Column(BaseModel):
    name: str
    data_type: str
    description: str | None = None
    unit: str | None = None
    nullable: bool | None = None


class TableDescription(BaseModel):
    database: str
    version: str
    table: str
    table_type: str | None = None
    description: str | None = None
    grain: str | None = None
    logical_key: list[str] = Field(default_factory=list)
    reporting_cycle: str | None = None
    columns: list[Column]
    joins: list[dict[str, Any]] = Field(default_factory=list)
    caveats: list[str] = Field(default_factory=list)
    source_links: list[str] = Field(default_factory=list)


class ValidationResult(BaseModel):
    valid: bool
    normalized_sql: str | None = None
    bounded_sql: str | None = None
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    tables: list[str] = Field(default_factory=list)
    columns: list[str] = Field(default_factory=list)
    has_order_by: bool = False
    row_limit: int | None = None


class SqlExplanation(BaseModel):
    validation: ValidationResult
    databases: list[str] = Field(default_factory=list)
    versions: list[str] = Field(default_factory=list)
    tables: list[str] = Field(default_factory=list)
    columns: list[str] = Field(default_factory=list)
    joins: int = 0
    aggregations: list[str] = Field(default_factory=list)
    filters: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    provenance_impact: str = "Result values are returned by EEA unless locally transformed."


class Provenance(BaseModel):
    provider: str = "EEA Discodata"
    database: str | None = None
    version: str | None = None
    tables: list[str] = Field(default_factory=list)
    query_hash: str
    retrieved_at: datetime
    reporting_status: ReportingStatus = "unknown"
    source_links: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class QueryResult(BaseModel):
    results: list[dict[str, Any]]
    page: int
    page_size: int
    returned_rows: int
    has_more: bool
    provenance: Provenance
