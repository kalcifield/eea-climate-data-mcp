from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from platformdirs import user_cache_path


class JsonCache:
    def __init__(self, root: Path | None = None) -> None:
        self.root = root or user_cache_path("eu-climate-policy")

    def get(self, key: str, ttl_seconds: int) -> Any | None:
        path = self.root / f"{key}.json"
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            if time.time() - payload["saved_at"] > ttl_seconds:
                return None
            return payload["value"]
        except (FileNotFoundError, KeyError, ValueError, OSError):
            return None

    def set(self, key: str, value: Any) -> None:
        try:
            self.root.mkdir(parents=True, exist_ok=True)
            target = self.root / f"{key}.json"
            target.write_text(
                json.dumps({"saved_at": time.time(), "value": value}), encoding="utf-8"
            )
        except OSError:
            # A read-only home directory must not make the public API unusable.
            return
