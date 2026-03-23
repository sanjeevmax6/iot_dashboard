import json

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


INTENT_GUARD_PROMPT = """\
You are a topic classifier for an industrial IoT fleet monitoring assistant.

Decide if the user's message is relevant to any of the following:
- Fleet or machine health, risk, or status
- Sensor data, telemetry, or readings (temperature, vibration, etc.)
- Maintenance, diagnostics, or recommended actions
- Questions about specific machine IDs or components
- Requests to run, explain, or compare an analysis

Reply with exactly one word — nothing else:
  ON_TOPIC   — if the message relates to any of the above
  OFF_TOPIC  — if the message is clearly unrelated (weather, coding, general knowledge, jokes, etc.)

Do not explain. Output only ON_TOPIC or OFF_TOPIC.\
"""


def build_user_prompt(
    summaries: list[dict],
    errors: list[str] | None = None,
    top_n: int | None = None,
) -> str:
    if top_n is not None:
        n = min(top_n, len(summaries))
        opening = f"Analyze the following {len(summaries)} machine(s) and return the top {n} at-risk."
    else:
        opening = (
            f"Analyze the following {len(summaries)} machine(s) and return ALL machines "
            "that have meaningful risk, ranked highest first. Do not artificially limit the count."
        )
    prompt = f"{opening}\n\nMachine summaries:\n{json.dumps(summaries, indent=2, default=str)}"
    if errors:
        prompt += "\n\nYour previous response failed validation. Fix ALL of the following:\n"
        prompt += "\n".join(f"  - {e}" for e in errors)
    return prompt
