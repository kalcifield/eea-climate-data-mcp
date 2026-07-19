from __future__ import annotations

import hashlib
import json
from typing import Any, cast

import httpx

from hun_climate_policy.cache import JsonCache
from hun_climate_policy.config import Settings
from hun_climate_policy.errors import UpstreamError


class DiscodataError(UpstreamError):
    def __init__(self, message: str, code: int | None = None) -> None:
        super().__init__(message)
        self.code = code


class DiscodataProvider:
    def __init__(self, settings: Settings | None = None, cache: JsonCache | None = None) -> None:
        self.settings = settings or Settings()
        self.cache = cache or JsonCache()

    def _get_json(
        self, path: str, params: dict[str, Any] | None = None, timeout: float | None = None
    ) -> Any:
        try:
            with httpx.Client(
                base_url=self.settings.base_url, timeout=timeout or self.settings.timeout_seconds
            ) as client:
                response = client.get(path, params=params)
                response.raise_for_status()
                data = response.json()
        except (httpx.HTTPError, json.JSONDecodeError) as exc:
            raise DiscodataError(f"Discodata request failed: {exc}") from exc
        if isinstance(data, dict) and data.get("errors"):
            first = data["errors"][0]
            raise DiscodataError(
                first.get("error", "Unknown Discodata error"), first.get("errorcode")
            )
        return data

    def metadata(self, no_cache: bool = False) -> list[dict[str, Any]]:
        key = "metadata"
        if not no_cache and (value := self.cache.get(key, 86400)) is not None:
            return cast(list[dict[str, Any]], value)
        value = cast(list[dict[str, Any]], self._get_json("/md"))
        self.cache.set(key, value)
        return value

    def query(
        self, sql: str, page: int, page_size: int, timeout: float | None = None
    ) -> list[dict[str, Any]]:
        payload = cast(
            dict[str, Any],
            self._get_json("/sql", {"query": sql, "p": page, "nrOfHits": page_size}, timeout),
        )
        return cast(list[dict[str, Any]], payload.get("results", []))

    @staticmethod
    def query_hash(sql: str) -> str:
        return hashlib.sha256(" ".join(sql.split()).encode()).hexdigest()
