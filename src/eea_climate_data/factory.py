from __future__ import annotations

import os

from eea_climate_data.config import Settings
from eea_climate_data.discodata import DiscodataProvider
from eea_climate_data.service import ClimatePolicyService


def create_service() -> ClimatePolicyService:
    settings = Settings(
        base_url=os.getenv("EEA_CLIMATE_DISCODATA_URL", "https://discodata.eea.europa.eu"),
        timeout_seconds=float(os.getenv("EEA_CLIMATE_TIMEOUT_SECONDS", "30")),
        max_page_size=int(os.getenv("EEA_CLIMATE_MAX_PAGE_SIZE", "1000")),
    )
    return ClimatePolicyService(DiscodataProvider(settings), settings)
