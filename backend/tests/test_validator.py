
from agent.schemas import AnalysisOutput, MachineRisk
from agent.validator import validate_logic

VALID_IDS = ["MCH-01", "MCH-02", "MCH-03", "MCH-04"]


def make_machine(
    machine_id="MCH-01",
    risk_level="high",
    risk_score=0.9,
    reason="Many errors",
    affected_sensors=None,
    recommended_action="Inspect immediately",
):
    return MachineRisk(
        machine_id=machine_id,
        risk_level=risk_level,
        risk_score=risk_score,
        reason=reason,
        affected_sensors=affected_sensors if affected_sensors is not None else ["temperature"],
        recommended_action=recommended_action,
    )


def make_output(machines=None, fleet_summary="Fleet is mostly healthy."):
    if machines is None:
        machines = [
            make_machine("MCH-01", "high", 0.91),
            make_machine("MCH-02", "medium", 0.55),
            make_machine("MCH-03", "low", 0.2),
        ]
    return AnalysisOutput(top_at_risk_machines=machines, fleet_summary=fleet_summary)


def test_valid_output_passes():
    errors = validate_logic(make_output(), VALID_IDS)
    assert errors == []


def test_wrong_count_too_few():
    output = make_output([make_machine("MCH-01", "high", 0.9)])
    errors = validate_logic(output, VALID_IDS)
    assert any("Expected exactly 3" in e for e in errors)


def test_wrong_count_too_many():
    machines = [
        make_machine("MCH-01", "high", 0.91),
        make_machine("MCH-02", "medium", 0.55),
        make_machine("MCH-03", "low", 0.2),
        make_machine("MCH-04", "low", 0.1),
    ]
    errors = validate_logic(make_output(machines), VALID_IDS)
    assert any("Expected exactly 3" in e for e in errors)


def test_unknown_machine_id():
    machines = [
        make_machine("MCH-GHOST", "high", 0.9),
        make_machine("MCH-02", "medium", 0.5),
        make_machine("MCH-03", "low", 0.2),
    ]
    errors = validate_logic(make_output(machines), VALID_IDS)
    assert any("MCH-GHOST" in e for e in errors)


def test_high_risk_score_too_low():
    machines = [
        make_machine("MCH-01", "high", 0.5),  # high needs >= 0.7
        make_machine("MCH-02", "medium", 0.4),
        make_machine("MCH-03", "low", 0.2),
    ]
    errors = validate_logic(make_output(machines), VALID_IDS)
    assert any("risk_level='high'" in e for e in errors)


def test_low_risk_score_too_high():
    machines = [
        make_machine("MCH-01", "high", 0.9),
        make_machine("MCH-02", "medium", 0.5),
        make_machine("MCH-03", "low", 0.8),  # low needs < 0.3
    ]
    errors = validate_logic(make_output(machines), VALID_IDS)
    assert any("risk_level='low'" in e for e in errors)


def test_high_risk_empty_sensors():
    machines = [
        make_machine("MCH-01", "high", 0.9, affected_sensors=[]),  # contradiction
        make_machine("MCH-02", "medium", 0.5),
        make_machine("MCH-03", "low", 0.2),
    ]
    errors = validate_logic(make_output(machines), VALID_IDS)
    assert any("affected_sensors is empty" in e for e in errors)


def test_duplicate_machine_ids():
    machines = [
        make_machine("MCH-01", "high", 0.9),
        make_machine("MCH-01", "medium", 0.5),  # duplicate
        make_machine("MCH-03", "low", 0.2),
    ]
    errors = validate_logic(make_output(machines), VALID_IDS)
    assert any("Duplicate" in e for e in errors)


def test_non_descending_scores():
    machines = [
        make_machine("MCH-01", "medium", 0.5),
        make_machine("MCH-02", "high", 0.9),  # higher score ranked second — wrong
        make_machine("MCH-03", "low", 0.2),
    ]
    errors = validate_logic(make_output(machines), VALID_IDS)
    assert any("descending order" in e for e in errors)


def test_empty_reason_fails():
    machines = [
        make_machine("MCH-01", "high", 0.9, reason="   "),
        make_machine("MCH-02", "medium", 0.5),
        make_machine("MCH-03", "low", 0.2),
    ]
    errors = validate_logic(make_output(machines), VALID_IDS)
    assert any("reason cannot be empty" in e for e in errors)


def test_fewer_than_3_machines_accepts_smaller_count():
    two_machine_ids = ["MCH-01", "MCH-02"]
    machines = [
        make_machine("MCH-01", "high", 0.9),
        make_machine("MCH-02", "medium", 0.5),
    ]
    output = AnalysisOutput(top_at_risk_machines=machines, fleet_summary="Only 2 machines.")
    errors = validate_logic(output, two_machine_ids)
    assert errors == []
