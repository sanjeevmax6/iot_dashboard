from agent.schemas import AnalysisOutput, MachineRisk
from app.core.config import settings

# risk_level → (min_score, max_score)
RISK_SCORE_BOUNDS: dict[str, tuple[float, float]] = {
    "high": (0.70, 1.00),
    "medium": (0.30, 0.69),
    "low": (0.00, 0.29),
}


def validate_logic(result: AnalysisOutput, valid_machine_ids: list[str]) -> list[str]:
    """
    Stage 2 validation: logic contradiction checks.
    Returns a list of error strings. Empty list means valid.
    """
    errors: list[str] = []
    valid_set = set(valid_machine_ids)
    expected_count = min(settings.top_at_risk_count, len(valid_machine_ids))
    actual_count = len(result.top_at_risk_machines)

    # Check result count matches what was requested
    if actual_count != expected_count:
        errors.append(
            f"Expected exactly {expected_count} machine(s) in top_at_risk_machines "
            f"(top_at_risk_count={settings.top_at_risk_count}, available machines={len(valid_machine_ids)}), "
            f"got {actual_count}."
        )

    # Check for duplicate machine IDs
    seen_ids: set[str] = set()
    for machine in result.top_at_risk_machines:
        if machine.machine_id in seen_ids:
            errors.append(f"Duplicate machine_id '{machine.machine_id}' in results.")
        seen_ids.add(machine.machine_id)

    # Per-machine checks
    for machine in result.top_at_risk_machines:
        errors.extend(_check_machine(machine, valid_set))

    # Risk scores must be non-ascending (rank 1 highest)
    scores = [m.risk_score for m in result.top_at_risk_machines]
    if scores != sorted(scores, reverse=True):
        errors.append(
            f"risk_scores must be in descending order (highest risk first). Got: {scores}"
        )

    return errors


def _check_machine(machine: MachineRisk, valid_set: set[str]) -> list[str]:
    errors: list[str] = []

    if machine.machine_id not in valid_set:
        errors.append(
            f"machine_id '{machine.machine_id}' does not exist in the dataset. "
            f"Valid IDs: {sorted(valid_set)}"
        )

    min_score, max_score = RISK_SCORE_BOUNDS[machine.risk_level]
    if not (min_score <= machine.risk_score <= max_score):
        errors.append(
            f"machine '{machine.machine_id}': risk_level='{machine.risk_level}' requires "
            f"risk_score between {min_score} and {max_score}, got {machine.risk_score}."
        )

    if machine.risk_level == "high" and len(machine.affected_sensors) == 0:
        errors.append(
            f"machine '{machine.machine_id}': risk_level='high' but affected_sensors is empty. "
            "High-risk machines must identify at least one affected sensor."
        )

    if not machine.reason.strip():
        errors.append(f"machine '{machine.machine_id}': reason cannot be empty.")

    if not machine.recommended_action.strip():
        errors.append(f"machine '{machine.machine_id}': recommended_action cannot be empty.")

    return errors
