from __future__ import annotations

from typing import Any

import pytest


@pytest.fixture
def metadata_fixture() -> list[dict[str, Any]]:
    return [
        {
            "database": "GHG_Inventory",
            "Schemas": [
                {
                    "name": "latest",
                    "Tables": [
                        {
                            "name": "ghg_value",
                            "tableType": "view",
                            "Columns": [
                                {
                                    "name": "country_code",
                                    "dataType": "nvarchar",
                                    "description": "Country code.",
                                },
                                {
                                    "name": "inventory_year",
                                    "dataType": "int",
                                    "description": "Year.",
                                },
                                {
                                    "name": "variable_uid",
                                    "dataType": "nvarchar",
                                    "description": "Variable key.",
                                },
                                {
                                    "name": "value",
                                    "dataType": "numeric",
                                    "description": "Reported value.",
                                },
                            ],
                        }
                    ],
                }
            ],
        },
        {
            "database": "GHGPAMS",
            "Schemas": [{"name": "latest", "Tables": []}],
        },
        {
            "database": "Unrelated",
            "Schemas": [{"name": "latest", "Tables": []}],
        },
    ]
