import pytest
from pydantic import ValidationError

from agent.schemas import AnalysisOutput, MachineRisk


def test_machine_risk_score_above_1_raises():
    with pytest.raises(ValidationError):
        MachineRisk(
            machine_id="MCH-01",
            risk_level="high",
            risk_score=1.5,
            reason="test",
            affected_sensors=[],
            recommended_action="act",
        )


def test_machine_risk_score_negative_raises():
    with pytest.raises(ValidationError):
        MachineRisk(
            machine_id="MCH-01",
            risk_level="low",
            risk_score=-0.1,
            reason="test",
            affected_sensors=[],
            recommended_action="act",
        )


def test_machine_risk_invalid_level_raises():
    with pytest.raises(ValidationError):
        MachineRisk(
            machine_id="MCH-01",
            risk_level="critical",
            risk_score=0.5,
            reason="test",
            affected_sensors=[],
            recommended_action="act",
        )


def test_analysis_output_empty_machines_raises():
    with pytest.raises(ValidationError, match="cannot be empty"):
        AnalysisOutput(top_at_risk_machines=[], fleet_summary="ok")


def test_analysis_output_valid():
    output = AnalysisOutput(
        top_at_risk_machines=[
            MachineRisk(
                machine_id="MCH-01",
                risk_level="high",
                risk_score=0.9,
                reason="many errors",
                affected_sensors=["temperature"],
                recommended_action="Inspect immediately",
            )
        ],
        fleet_summary="Fleet is at risk.",
    )
    assert output.top_at_risk_machines[0].machine_id == "MCH-01"
    assert output.fleet_summary == "Fleet is at risk."


def test_machine_risk_boundary_scores_are_valid():
    # Boundary values that should be valid
    MachineRisk(machine_id="X", risk_level="high", risk_score=1.0,
                reason="r", affected_sensors=[], recommended_action="a")
    MachineRisk(machine_id="X", risk_level="low", risk_score=0.0,
                reason="r", affected_sensors=[], recommended_action="a")
