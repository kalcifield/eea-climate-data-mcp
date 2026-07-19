from typing import Any

EEA_CLIMATE_PROFILE: dict[str, Any] = {
    "tables": {
        "GHG_Inventory.latest.ghg_value": {
            "grain": "country × submission × inventory year × variable",
            "logical_key": ["country_code", "submission_version", "inventory_year", "variable_uid"],
            "reporting_cycle": "annual national GHG inventory submission",
            "status": "reported_actual",
            "joins": [
                {
                    "to": "GHG_Inventory.latest.ghg_variable",
                    "on": "variable_uid",
                    "cardinality": "many-to-one",
                }
            ],
            "caveats": [
                "isCalculatedByEEA=1 identifies EEA-calculated rather than directly reported values."
            ],
        },
        "GHG_Inventory.latest.ghg_variable": {
            "grain": "GHG inventory variable",
            "logical_key": ["variable_uid"],
            "reporting_cycle": "aligned with inventory dataset",
            "status": "reported_actual",
        },
        "GHG_Inventory.latest.ghg_meta": {
            "grain": "country × submission version",
            "logical_key": ["country_code", "submission_version"],
            "reporting_cycle": "annual",
            "status": "reported_actual",
        },
        "GHGPAMS.latest.annexIX_flat_view_PaMs_elasticsearch": {
            "grain": "reported policy or measure record (flat reporting view)",
            "logical_key": ["Country", "Report_ID", "ID_of_policy_or_measure"],
            "reporting_cycle": "Governance Regulation policy-and-measures reporting cycle",
            "status": "reported_policy_estimate",
            "caveats": ["Quantified ex-ante and ex-post fields are sparse; null is not zero."],
        },
    },
}
