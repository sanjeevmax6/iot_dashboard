"""
Conversational analyst agent with session memory and token streaming.

Session memory: in-memory dict of session_id → InMemoryChatMessageHistory.
Resets on server restart — acceptable for this scope.

Streaming: uses ChatModel.astream() to yield tokens as they arrive.
SSE event types:
  {"type": "thinking_token", "content": "..."}  — streamed token
  {"type": "done",           "message": "..."}  — full response, signals completion
  {"type": "error",          "message": "..."}  — failure
"""

import json
from collections.abc import AsyncGenerator
from typing import Any

from langchain_core.chat_history import InMemoryChatMessageHistory
from langchain_core.runnables.history import RunnableWithMessageHistory

from agent.llm_rerouter import get_llm
from agent.schemas import AnalysisOutput

# ── Session store ────────────────────────────────────────────────────────────

_sessions: dict[str, InMemoryChatMessageHistory] = {}


def get_or_create_session(session_id: str) -> InMemoryChatMessageHistory:
    if session_id not in _sessions:
        _sessions[session_id] = InMemoryChatMessageHistory()
    return _sessions[session_id]


# ── System prompt ────────────────────────────────────────────────────────────

def _build_system_prompt(analysis: AnalysisOutput | None) -> str:
    base = (
        "You are an industrial fleet analyst. "
        "You help maintenance teams understand machine health, diagnose issues, "
        "and plan interventions based on sensor data and AI risk assessments. "
        "Be concise, precise, and speak in plain language a plant operator can act on."
    )
    if analysis is None:
        return base + (
            "\n\nNo analysis has been run yet. "
            "If asked about machine risk, tell the user to run an analysis first."
        )

    machines_summary = "\n".join(
        f"- {m.machine_id}: {m.risk_level} risk (score {m.risk_score:.2f}) — {m.reason}"
        for m in analysis.top_at_risk_machines
    )
    return (
        f"{base}\n\n"
        f"Latest fleet analysis results:\n{machines_summary}\n\n"
        f"Fleet summary: {analysis.fleet_summary}\n\n"
        "Use these findings to answer follow-up questions. "
        "You may reference specific machine IDs, risk scores, and sensor data. "
        "Do not fabricate machine IDs or metrics not present above."
    )


# ── Streaming chat ────────────────────────────────────────────────────────────

async def stream_chat(
    session_id: str,
    user_message: str,
    analysis: AnalysisOutput | None,
) -> AsyncGenerator[dict[str, Any], None]:
    history = get_or_create_session(session_id)
    llm = get_llm()

    system_prompt = _build_system_prompt(analysis)

    # Build the runnable: system message is injected fresh each call so it
    # always reflects the latest analysis; history carries the conversation.
    from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        MessagesPlaceholder(variable_name="history"),
        ("human", "{input}"),
    ])

    chain = prompt | llm

    runnable = RunnableWithMessageHistory(
        chain,
        lambda _sid: history,
        input_messages_key="input",
        history_messages_key="history",
    )

    full_response = ""
    try:
        async for chunk in runnable.astream(
            {"input": user_message},
            config={"configurable": {"session_id": session_id}},
        ):
            token = chunk.content if hasattr(chunk, "content") else str(chunk)
            if token:
                full_response += token
                yield {"type": "thinking_token", "content": token}

        yield {"type": "done", "message": full_response}

    except Exception as exc:
        yield {"type": "error", "message": str(exc)}


# ── Narrate analysis results ──────────────────────────────────────────────────

async def narrate_analysis(
    session_id: str,
    analysis: AnalysisOutput,
) -> AsyncGenerator[dict[str, Any], None]:
    """
    Called after run_analysis() completes. Asks the LLM to narrate the
    structured findings conversationally. Result goes into session memory.
    """
    machines_json = json.dumps(
        [m.model_dump() for m in analysis.top_at_risk_machines], indent=2
    )
    prompt = (
        f"I've completed the fleet analysis. Here are the structured findings:\n\n"
        f"{machines_json}\n\n"
        f"Fleet summary: {analysis.fleet_summary}\n\n"
        "Please introduce these results to the user in a clear, conversational way. "
        "Highlight the most urgent machine first, explain the key risk factors, "
        "and close with a brief overall fleet health statement. "
        "Be direct — one paragraph per machine, no bullet lists."
    )

    async for event in stream_chat(session_id, prompt, analysis):
        yield event
