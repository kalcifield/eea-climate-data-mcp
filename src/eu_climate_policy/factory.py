from __future__ import annotations

import os

from eu_climate_policy.config import Settings
from eu_climate_policy.discodata import DiscodataProvider
from eu_climate_policy.service import ClimatePolicyService


def create_service() -> ClimatePolicyService:
    settings = Settings(
        base_url=os.getenv("EU_CLIMATE_DISCODATA_URL", "https://discodata.eea.europa.eu"),
        timeout_seconds=float(os.getenv("EU_CLIMATE_TIMEOUT_SECONDS", "30")),
        max_page_size=int(os.getenv("EU_CLIMATE_MAX_PAGE_SIZE", "1000")),
    )
    return ClimatePolicyService(DiscodataProvider(settings), settings)
