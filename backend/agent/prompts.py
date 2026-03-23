import json

from app.core.config import settings

SYSTEM_PROMPT = """\
You are an industrial equipment risk analyst. You will be given telemetry summaries \
for a fleet of machines and must identify the top at-risk machines based on error rates, \
warning rates, and sensor readings.

Rules:
- Rank machines strictly by risk, highest first.
- risk_score must be a float between 0.0 and 1.0. It MUST fall within the exact range for its risk_level:
    high   → risk_score MUST be 0.70 or above   (e.g. 0.75, 0.85, 0.92)
    medium → risk_score MUST be between 0.30 and 0.69 inclusive (e.g. 0.35, 0.50, 0.65)
    low    → risk_score MUST be 0.29 or below   (e.g. 0.05, 0.15, 0.25)
- Do NOT assign a risk_score that is outside the range for the chosen risk_level.
- affected_sensors must list which sensors show anomalies (e.g. ["temperature", "vibration"]).
- If risk_level is high, affected_sensors cannot be empty.
- Only include machines that actually appear in the provided summaries.
- Return a fleet_summary: one sentence describing the overall fleet health.\
"""


def build_user_prompt(summaries: list[dict], errors: list[str] | None = None) -> str:
    n = min(settings.top_at_risk_count, len(summaries))
    prompt = (
        f"Analyze the following {len(summaries)} machine(s) and return the top {n} at-risk.\n\n"
        f"Machine summaries:\n{json.dumps(summaries, indent=2, default=str)}"
    )
    if errors:
        prompt += "\n\nYour previous response failed validation. Fix ALL of the following:\n"
        prompt += "\n".join(f"  - {e}" for e in errors)
    return prompt
