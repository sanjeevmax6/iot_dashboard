from agent.prompts import SYSTEM_PROMPT, build_user_prompt

SUMMARIES = [
    {"machine_id": "MCH-01", "error_rate": 0.10},
    {"machine_id": "MCH-02", "error_rate": 0.05},
    {"machine_id": "MCH-03", "error_rate": 0.01},
    {"machine_id": "MCH-04", "error_rate": 0.00},
]


def test_build_user_prompt_includes_machine_count():
    prompt = build_user_prompt(SUMMARIES, top_n=3)
    assert "4 machine(s)" in prompt
    assert "top 3" in prompt


def test_build_user_prompt_serialises_summaries():
    prompt = build_user_prompt(SUMMARIES)
    assert "MCH-01" in prompt
    assert "MCH-04" in prompt


def test_build_user_prompt_no_errors_section():
    prompt = build_user_prompt(SUMMARIES)
    assert "previous response failed" not in prompt


def test_build_user_prompt_with_errors_appends_section():
    errors = ["risk_score out of range for high", "duplicate machine_id MCH-01"]
    prompt = build_user_prompt(SUMMARIES, errors)
    assert "previous response failed validation" in prompt
    assert "risk_score out of range for high" in prompt
    assert "duplicate machine_id MCH-01" in prompt


def test_build_user_prompt_empty_errors_list_omits_section():
    prompt = build_user_prompt(SUMMARIES, errors=[])
    assert "previous response" not in prompt


def test_build_user_prompt_fewer_than_3_machines():
    prompt = build_user_prompt([{"machine_id": "MCH-01"}], top_n=1)
    assert "top 1" in prompt


def test_build_user_prompt_exactly_3_machines():
    prompt = build_user_prompt(SUMMARIES[:3], top_n=3)
    assert "top 3" in prompt


def test_build_user_prompt_flexible_mode():
    # No top_n → flexible mode, should not constrain count
    prompt = build_user_prompt(SUMMARIES)
    assert "4 machine(s)" in prompt
    assert "ALL machines" in prompt
    assert "top" not in prompt


def test_system_prompt_contains_risk_rules():
    assert "risk_score" in SYSTEM_PROMPT
    assert "high" in SYSTEM_PROMPT
    assert "medium" in SYSTEM_PROMPT
    assert "low" in SYSTEM_PROMPT
    assert "affected_sensors" in SYSTEM_PROMPT
