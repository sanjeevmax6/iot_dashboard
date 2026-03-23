from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from agent.chat import (
    _build_system_prompt,
    _sessions,
    get_or_create_session,
    narrate_analysis,
    stream_chat,
)
from agent.schemas import AnalysisOutput, MachineRisk

MOCK_ANALYSIS = AnalysisOutput(
    top_at_risk_machines=[
        MachineRisk(
            machine_id="MCH-01",
            risk_level="high",
            risk_score=0.92,
            reason="High error rate detected",
            affected_sensors=["temperature", "vibration"],
            recommended_action="Schedule immediate inspection",
        ),
        MachineRisk(
            machine_id="MCH-02",
            risk_level="medium",
            risk_score=0.50,
            reason="Elevated warnings",
            affected_sensors=["vibration"],
            recommended_action="Monitor closely",
        ),
    ],
    fleet_summary="Fleet requires attention on two machines.",
)


# ── Session management ──────────────────────────────────────────────────────

def test_get_or_create_session_creates_new_session():
    _sessions.clear()
    session = get_or_create_session("new-session")
    assert session is not None
    assert "new-session" in _sessions


def test_get_or_create_session_returns_same_object():
    _sessions.clear()
    s1 = get_or_create_session("shared-session")
    s2 = get_or_create_session("shared-session")
    assert s1 is s2


def test_get_or_create_session_isolates_different_sessions():
    _sessions.clear()
    s1 = get_or_create_session("session-A")
    s2 = get_or_create_session("session-B")
    assert s1 is not s2


# ── System prompt ───────────────────────────────────────────────────────────

def test_build_system_prompt_without_analysis():
    prompt = _build_system_prompt(None)
    assert "No analysis has been run yet" in prompt
    assert "run an analysis first" in prompt


def test_build_system_prompt_with_analysis_includes_machines():
    prompt = _build_system_prompt(MOCK_ANALYSIS)
    assert "MCH-01" in prompt
    assert "MCH-02" in prompt
    assert "high" in prompt
    assert "0.92" in prompt


def test_build_system_prompt_with_analysis_includes_fleet_summary():
    prompt = _build_system_prompt(MOCK_ANALYSIS)
    assert "Fleet requires attention on two machines." in prompt


def test_build_system_prompt_with_analysis_warns_not_to_fabricate():
    prompt = _build_system_prompt(MOCK_ANALYSIS)
    assert "Do not fabricate" in prompt


# ── stream_chat ─────────────────────────────────────────────────────────────

def _make_fake_astream(tokens: list[str]):
    """Returns an async generator function that yields chunks for each token."""
    async def fake_astream(*args, **kwargs):
        for token in tokens:
            chunk = MagicMock()
            chunk.content = token
            yield chunk
    return fake_astream


@pytest.mark.asyncio
async def test_stream_chat_yields_thinking_tokens():
    _sessions.clear()
    mock_runnable = MagicMock()
    mock_runnable.astream = _make_fake_astream(["Hello", ", ", "world"])

    with patch("agent.chat.get_llm"):
        with patch("agent.chat.RunnableWithMessageHistory", return_value=mock_runnable):
            events = [e async for e in stream_chat("sid-1", "How are things?", None)]

    thinking = [e for e in events if e["type"] == "thinking_token"]
    assert len(thinking) == 3
    assert thinking[0]["content"] == "Hello"


@pytest.mark.asyncio
async def test_stream_chat_yields_done_with_full_message():
    _sessions.clear()
    mock_runnable = MagicMock()
    mock_runnable.astream = _make_fake_astream(["Hello", " world"])

    with patch("agent.chat.get_llm"):
        with patch("agent.chat.RunnableWithMessageHistory", return_value=mock_runnable):
            events = [e async for e in stream_chat("sid-2", "hello?", None)]

    done = next(e for e in events if e["type"] == "done")
    assert done["message"] == "Hello world"


@pytest.mark.asyncio
async def test_stream_chat_yields_error_on_llm_failure():
    _sessions.clear()

    async def failing_astream(*args, **kwargs):
        raise RuntimeError("LLM connection failed")
        yield  # pragma: no cover

    mock_runnable = MagicMock()
    mock_runnable.astream = failing_astream

    with patch("agent.chat.get_llm"):
        with patch("agent.chat.RunnableWithMessageHistory", return_value=mock_runnable):
            events = [e async for e in stream_chat("sid-3", "hello?", None)]

    assert len(events) == 1
    assert events[0]["type"] == "error"
    assert "LLM connection failed" in events[0]["message"]


@pytest.mark.asyncio
async def test_stream_chat_skips_empty_tokens():
    _sessions.clear()
    mock_runnable = MagicMock()
    mock_runnable.astream = _make_fake_astream(["", "real content", ""])

    with patch("agent.chat.get_llm"):
        with patch("agent.chat.RunnableWithMessageHistory", return_value=mock_runnable):
            events = [e async for e in stream_chat("sid-4", "hi", None)]

    thinking = [e for e in events if e["type"] == "thinking_token"]
    assert len(thinking) == 1
    assert thinking[0]["content"] == "real content"


@pytest.mark.asyncio
async def test_stream_chat_with_analysis_context():
    _sessions.clear()
    mock_runnable = MagicMock()
    mock_runnable.astream = _make_fake_astream(["MCH-01 is critical."])

    with patch("agent.chat.get_llm"):
        with patch("agent.chat.RunnableWithMessageHistory", return_value=mock_runnable):
            events = [e async for e in stream_chat("sid-5", "which machine?", MOCK_ANALYSIS)]

    done = next(e for e in events if e["type"] == "done")
    assert "MCH-01" in done["message"]


# ── narrate_analysis ────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_narrate_analysis_yields_done_event():
    _sessions.clear()
    mock_runnable = MagicMock()
    mock_runnable.astream = _make_fake_astream(["Fleet analysis complete."])

    with patch("agent.chat.get_llm"):
        with patch("agent.chat.RunnableWithMessageHistory", return_value=mock_runnable):
            events = [e async for e in narrate_analysis("sid-6", MOCK_ANALYSIS)]

    done = next(e for e in events if e["type"] == "done")
    assert done["message"] == "Fleet analysis complete."


@pytest.mark.asyncio
async def test_narrate_analysis_streams_tokens():
    _sessions.clear()
    mock_runnable = MagicMock()
    mock_runnable.astream = _make_fake_astream(["MCH-01", " needs", " attention."])

    with patch("agent.chat.get_llm"):
        with patch("agent.chat.RunnableWithMessageHistory", return_value=mock_runnable):
            events = [e async for e in narrate_analysis("sid-7", MOCK_ANALYSIS)]

    thinking = [e for e in events if e["type"] == "thinking_token"]
    assert len(thinking) == 3


# ── Chat route (SSE endpoint) ───────────────────────────────────────────────

@pytest.mark.asyncio
async def test_chat_stream_followup_question(client):
    _sessions.clear()
    mock_runnable = MagicMock()
    mock_runnable.astream = _make_fake_astream(["All machines are fine."])

    with patch("agent.chat.get_llm"):
        with patch("agent.chat.RunnableWithMessageHistory", return_value=mock_runnable):
            resp = await client.post(
                "/api/analysis/chat/stream",
                json={"message": "How is the fleet?", "session_id": "test-1", "trigger_analysis": False},
            )

    assert resp.status_code == 200
    assert '"type": "done"' in resp.text
    assert "All machines are fine." in resp.text


@pytest.mark.asyncio
async def test_chat_stream_trigger_with_no_data_returns_error(client):
    _sessions.clear()
    # The chat route opens its own AsyncSessionLocal session (not the test DB),
    # so mock get_machine_summaries to return empty to simulate no ingested data.
    with patch("app.services.summarizer.get_machine_summaries", new_callable=AsyncMock, return_value=[]):
        resp = await client.post(
            "/api/analysis/chat/stream",
            json={"message": "", "session_id": "test-2", "trigger_analysis": True},
        )
    assert resp.status_code == 200
    assert '"type": "error"' in resp.text
    assert "No log data" in resp.text
