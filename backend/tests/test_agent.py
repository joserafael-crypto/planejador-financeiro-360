from decimal import Decimal
from app.services.agent import simulate_cashflow

def test_simulation_deterministic():
    out=simulate_cashflow({"cash_balance":1000,"income_total":5000,"expense_total":3000},2)
    assert out["ending_balance"]==5000.0 and len(out["series"])==2

def test_simulation_limits_horizon():
    assert simulate_cashflow({"cash_balance":0,"income_total":100,"expense_total":50},999)["months"]==120

from app.services.agent import SimulationArgs, TOOL_DEFINITIONS, tool_schemas


def test_ai_tool_registry_is_read_only_and_strict():
    assert TOOL_DEFINITIONS
    assert all(spec["read_only"] for spec in TOOL_DEFINITIONS.values())
    schemas = tool_schemas()
    assert {s["name"] for s in schemas} == set(TOOL_DEFINITIONS)
    assert all(s["strict"] is True for s in schemas)
    assert all(s["parameters"]["additionalProperties"] is False for s in schemas)


def test_simulation_arguments_reject_unknown_fields():
    try:
        SimulationArgs(foo=1)
        assert False, "unknown fields must be rejected"
    except Exception:
        pass
