from unittest.mock import MagicMock, patch

import pytest

from agent.graph import run_analysis
from agent.schemas import AnalysisOutput, MachineRisk

SUMMARIES = [
    {"machine_id": "MCH-01", "error_count": 4, "warning_count": 10, "total_readings": 100,
     "error_rate": 0.04, "warning_rate": 0.10, "avg_temperature": 85.0, "max_temperature": 102.0,
     "avg_vibration": 0.8, "max_vibration": 1.2, "operational_count": 86, "last_seen": "2026-03-04"},
    {"machine_id": "MCH-02", "error_count": 1, "warning_count": 5, "total_readings": 100,
     "error_rate": 0.01, "warning_rate": 0.05, "avg_temperature": 70.0, "max_temperature": 80.0,
     "avg_vibration": 0.4, "max_vibration": 0.6, "operational_count": 94, "last_seen": "2026-03-04"},
    {"machine_id": "MCH-03", "error_count": 0, "warning_count": 2, "total_readings": 100,
     "error_rate": 0.00, "warning_rate": 0.02, "avg_temperature": 60.0, "max_temperature": 65.0,
     "avg_vibration": 0.2, "max_vibration": 0.3, "operational_count": 98, "last_seen": "2026-03-04"},
]

VALID_OUTPUT = AnalysisOutput(
    top_at_risk_machines=[
        MachineRisk(machine_id="MCH-01", risk_level="high", risk_score=0.92,
                    reason="4 errors", affected_sensors=["temperature"], recommended_action="Inspect"),
        MachineRisk(machine_id="MCH-02", risk_level="medium", risk_score=0.45,
                    reason="1 error", affected_sensors=["vibration"], recommended_action="Monitor"),
        MachineRisk(machine_id="MCH-03", risk_level="low", risk_score=0.1,
                    reason="Minimal issues", affected_sensors=[], recommended_action="Routine check"),
    ],
    fleet_summary="Fleet is mostly healthy.",
)


def _make_mock_llm(return_value):
    """Returns a mock LLM whose .with_structured_output().invoke() returns the given value."""
    mock_structured = MagicMock()
    mock_structured.invoke = MagicMock(return_value=return_value)
    mock_llm = MagicMock()
    mock_llm.with_structured_output = MagicMock(return_value=mock_structured)
    return mock_llm


@pytest.mark.asyncio
async def test_happy_path_returns_result():
    with patch("agent.graph.get_llm", return_value=_make_mock_llm(VALID_OUTPUT)):
        state = await run_analysis(SUMMARIES)

    assert state["error_state"] is None
    assert state["parsed_result"] is not None
    assert state["parsed_result"].top_at_risk_machines[0].machine_id == "MCH-01"
    assert state["retry_count"] == 1


@pytest.mark.asyncio
async def test_validation_failure_triggers_retry():
    # First call returns invalid output (bad score for high risk), second returns valid
    bad_output = AnalysisOutput(
        top_at_risk_machines=[
            MachineRisk(machine_id="MCH-01", risk_level="high", risk_score=0.3,  # contradiction
                        reason="r", affected_sensors=["temperature"], recommended_action="a"),
            MachineRisk(machine_id="MCH-02", risk_level="medium", risk_score=0.45,
                        reason="r", affected_sensors=["vibration"], recommended_action="a"),
            MachineRisk(machine_id="MCH-03", risk_level="low", risk_score=0.1,
                        reason="r", affected_sensors=[], recommended_action="a"),
        ],
        fleet_summary="summary",
    )

    mock_structured = MagicMock()
    mock_structured.invoke = MagicMock(side_effect=[bad_output, VALID_OUTPUT])
    mock_llm = MagicMock()
    mock_llm.with_structured_output = MagicMock(return_value=mock_structured)

    with patch("agent.graph.get_llm", return_value=mock_llm):
        state = await run_analysis(SUMMARIES)

    assert state["error_state"] is None
    assert state["retry_count"] == 2


@pytest.mark.asyncio
async def test_llm_exception_triggers_retry():
    mock_structured = MagicMock()
    mock_structured.invoke = MagicMock(side_effect=[Exception("API timeout"), VALID_OUTPUT])
    mock_llm = MagicMock()
    mock_llm.with_structured_output = MagicMock(return_value=mock_structured)

    with patch("agent.graph.get_llm", return_value=mock_llm):
        state = await run_analysis(SUMMARIES)

    assert state["error_state"] is None
    assert state["retry_count"] == 2


@pytest.mark.asyncio
async def test_exhausted_retries_sets_error_state():
    bad_output = AnalysisOutput(
        top_at_risk_machines=[
            MachineRisk(machine_id="MCH-01", risk_level="high", risk_score=0.1,  # always invalid
                        reason="r", affected_sensors=["temperature"], recommended_action="a"),
            MachineRisk(machine_id="MCH-02", risk_level="medium", risk_score=0.5,
                        reason="r", affected_sensors=[], recommended_action="a"),
            MachineRisk(machine_id="MCH-03", risk_level="low", risk_score=0.2,
                        reason="r", affected_sensors=[], recommended_action="a"),
        ],
        fleet_summary="summary",
    )

    with patch("agent.graph.get_llm", return_value=_make_mock_llm(bad_output)):
        state = await run_analysis(SUMMARIES)

    assert state["error_state"] is not None
    assert "failed" in state["error_state"].lower()
    assert state["parsed_result"] is None
