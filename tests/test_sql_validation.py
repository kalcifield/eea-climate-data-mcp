from eea_climate_data.config import Settings
from eea_climate_data.sql_validation import SqlGuardrails


def guardrails() -> SqlGuardrails:
    return SqlGuardrails(Settings())


def test_accepts_and_bounds_country_select() -> None:
    result = guardrails().validate(
        "SELECT inventory_year, SUM(value) AS total "
        "FROM [GHG_Inventory].[latest].[ghg_value] "
        "WHERE country_code='DE' GROUP BY inventory_year",
        max_rows=50,
    )
    assert result.valid
    assert result.bounded_sql is not None
    assert "TOP 50" in result.bounded_sql
    assert result.tables == ["GHG_Inventory.latest.ghg_value"]


def test_rejects_multiple_statements() -> None:
    result = guardrails().validate(
        "SELECT * FROM [GHG_Inventory].[latest].[ghg_value]; "
        "SELECT * FROM [GHG_Inventory].[latest].[ghg_value]"
    )
    assert not result.valid
    assert "Exactly one" in result.errors[0]


def test_rejects_writes_cte_and_select_into() -> None:
    cases = [
        "DELETE FROM [GHG_Inventory].[latest].[ghg_value]",
        "WITH x AS (SELECT * FROM [GHG_Inventory].[latest].[ghg_value]) SELECT * FROM x",
        "SELECT * INTO x FROM [GHG_Inventory].[latest].[ghg_value]",
    ]
    for sql in cases:
        assert not guardrails().validate(sql).valid


def test_rejects_unqualified_and_non_allowlisted_tables() -> None:
    assert not guardrails().validate("SELECT * FROM ghg_value").valid
    assert not guardrails().validate("SELECT * FROM [EUNIS].[latest].[species]").valid


def test_rejects_unaliased_computed_column() -> None:
    result = guardrails().validate("SELECT COUNT(*) FROM [GHG_Inventory].[latest].[ghg_value]")
    assert not result.valid
    assert any("alias" in error for error in result.errors)


def test_rejects_excessive_top() -> None:
    result = guardrails().validate(
        "SELECT TOP 1000 * FROM [GHG_Inventory].[latest].[ghg_value]", max_rows=10
    )
    assert not result.valid
    assert result.row_limit == 1000


def test_explain_flags_join_risk() -> None:
    explanation = guardrails().explain(
        "SELECT v.value, x.sector FROM [GHG_Inventory].[latest].[ghg_value] v "
        "JOIN [GHG_Inventory].[latest].[ghg_variable] x ON v.variable_uid=x.variable_uid"
    )
    assert explanation.joins == 1
    assert any("cardinality" in risk for risk in explanation.risks)
