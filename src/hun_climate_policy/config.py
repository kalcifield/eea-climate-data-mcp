from __future__ import annotations

from pydantic import BaseModel, Field


class Settings(BaseModel):
    base_url: str = "https://discodata.eea.europa.eu"
    timeout_seconds: float = Field(default=30.0, ge=1, le=120)
    max_page_size: int = Field(default=1000, ge=1, le=5000)
    allowed_databases: frozenset[str] = frozenset({"GHG_Inventory", "GHGPAMS"})
    allowed_versions: frozenset[str] = frozenset(
        {
            "latest",
            "v1",
            "v1r1",
            "v2",
            "v2r1",
            "v2r2",
            "v21",
            "v21r1",
            "v23",
            "v23r1",
            "v25",
            "v25r1",
        }
    )
