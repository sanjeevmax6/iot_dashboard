import json

SYSTEM_PROMPT = """\
You are an industrial equipment risk analyst. You will be given telemetry summaries \
for a fleet of machines and must identify the top at-risk machines based on error rates, \
warning rates, and sensor readings.

Rules:
- Rank machines strictly by risk, highest first.
- risk_score must be a float between 0.0 and 1.0 and must be consistent with risk_level:
    high   → risk_score >= 0.7
    medium → 0.3 <= risk_score < 0.7
    low    → risk_score < 0.3
- affected_sensors must list which sensors show anomalies (e.g. ["temperature", "vibration"]).
- If risk_level is high, affected_sensors cannot be empty.
- Only include machines that actually appear in the provided summaries.
- Return a fleet_summary: one sentence describing the overall fleet health.\
"""


def build_user_prompt(summaries: list[dict], errors: list[str] | None = None) -> str:
    n = min(3, len(summaries))
    prompt = (
        f"Analyze the following {len(summaries)} machine(s) and return the top {n} at-risk.\n\n"
        f"Machine summaries:\n{json.dumps(summaries, indent=2, default=str)}"
    )
    if errors:
        prompt += "\n\nYour previous response failed validation. Fix ALL of the following:\n"
        prompt += "\n".join(f"  - {e}" for e in errors)
    return prompt
