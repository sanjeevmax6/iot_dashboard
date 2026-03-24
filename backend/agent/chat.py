"""
Conversational analyst agent with session memory and token streaming.

Session memory: in-memory dict of session_id → InMemoryChatMessageHistory.Resets on server restart

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
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables.history import RunnableWithMessageHistory

from agent.llm_rerouter import get_llm
from agent.prompts import INTENT_GUARD_PROMPT
from agent.schemas import AnalysisOutput
from app.core.logger import get_logger

logger = get_logger(__name__)

# ── Intent guard ─────────────────────────────────────────────────────────────

REFUSAL_MESSAGE = (
    "I can only help with questions about your fleet and machine data. "
    "Try clicking **Analyze fleet health** to run a fresh analysis, "
    "or ask me about a specific machine, sensor reading, or risk score."
)


async def classify_intent(user_message: str) -> bool:
    """
    Returns True if the message is on-topic (fleet/machine domain).
    Returns False if it is off-topic and should be refused.
    Fails open on error — better to answer an off-topic question
    than to incorrectly refuse a legitimate one.
    """
    llm = get_llm()
    try:
        response = await llm.ainvoke([
            SystemMessage(content=INTENT_GUARD_PROMPT),
            HumanMessage(content=user_message),
        ])
        result = response.content.strip().upper() == "ON_TOPIC"
        logger.info("Intent classification is complete, result is %s", "on topic" if result else "off topic")
        return result
    except Exception as exc:
        logger.warning("Intent classification failed, failing open, error is %s", exc)
        return True


# Session store

_sessions: dict[str, InMemoryChatMessageHistory] = {}


def get_or_create_session(session_id: str) -> InMemoryChatMessageHistory:
    if session_id not in _sessions:
        _sessions[session_id] = InMemoryChatMessageHistory()
    return _sessions[session_id]


# System prompt

def _build_system_prompt(
    analysis: AnalysisOutput | None,
    summaries: list[dict] | None = None,
) -> str:
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
    prompt = (
        f"{base}\n\n"
        f"Latest fleet analysis results:\n{machines_summary}\n\n"
        f"Fleet summary: {analysis.fleet_summary}\n\n"
        "Use these findings to answer follow-up questions. "
        "You may reference specific machine IDs, risk scores, and sensor data. "
        "Do not fabricate machine IDs or metrics not present above."
    )

    if summaries:
        prompt += f"\n\nRaw sensor data (all machines):\n{json.dumps(summaries, indent=2)}"

    return prompt


# Streaming chat

async def stream_chat(
    session_id: str,
    user_message: str,
    analysis: AnalysisOutput | None,
    summaries: list[dict] | None = None,
) -> AsyncGenerator[dict[str, Any], None]:
    history = get_or_create_session(session_id)
    llm = get_llm()

    system_prompt = _build_system_prompt(analysis, summaries)


    prompt = ChatPromptTemplate.from_messages([
        SystemMessage(content=system_prompt),
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

    logger.info("Starting chat stream, session_id is %s", session_id)
    full_response = ""
    try:
        async for chunk in runnable.astream(
            {"input": user_message},
            config={"configurable": {"session_id": session_id}},
        ):
            raw = chunk.content if hasattr(chunk, "content") else str(chunk)
            if isinstance(raw, list):
                token = "".join(
                    item.get("text", "") if isinstance(item, dict) else str(item)
                    for item in raw
                )
            else:
                token = raw
            if token:
                full_response += token
                yield {"type": "thinking_token", "content": token}

        logger.info("Chat stream is complete, session_id is %s, response length is %d characters", session_id, len(full_response))
        yield {"type": "done", "message": full_response}

    except Exception as exc:
        logger.error("Chat stream failed, session_id is %s, error is %s", session_id, exc)
        yield {"type": "error", "message": str(exc)}


# Narrate analysis results

async def narrate_analysis(
    session_id: str,
    analysis: AnalysisOutput,
    summaries: list[dict] | None = None,
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

    async for event in stream_chat(session_id, prompt, analysis, summaries):
        yield event
