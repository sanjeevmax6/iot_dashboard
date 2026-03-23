from typing import TypedDict

from backend.agent.llm_rerouter import get_llm
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import END, START, StateGraph

from agent.prompts import SYSTEM_PROMPT, build_user_prompt
from agent.schemas import AnalysisOutput
from agent.validator import validate_logic
from app.core.config import settings


class AnalysisState(TypedDict):
    machine_summaries: list[dict]
    valid_machine_ids: list[str]
    parsed_result: AnalysisOutput | None
    validation_errors: list[str]
    retry_count: int
    error_state: str | None


def invoke_llm(state: AnalysisState) -> AnalysisState:
    llm = get_llm().with_structured_output(AnalysisOutput)
    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=build_user_prompt(state["machine_summaries"], state["validation_errors"])),
    ]
    try:
        result = llm.invoke(messages)
        return {**state, "parsed_result": result, "retry_count": state["retry_count"] + 1}
    except Exception as exc:
        return {
            **state,
            "parsed_result": None,
            "validation_errors": state["validation_errors"] + [f"LLM call failed: {exc}"],
            "retry_count": state["retry_count"] + 1,
        }


def validate(state: AnalysisState) -> AnalysisState:
    if state["parsed_result"] is None:
        return state  # errors already set by invoke_llm

    errors = validate_logic(state["parsed_result"], state["valid_machine_ids"])
    if errors:
        return {**state, "parsed_result": None, "validation_errors": errors}
    return {**state, "validation_errors": []}


def summarize(state: AnalysisState) -> AnalysisState:
    if state["validation_errors"]:
        detail = "; ".join(state["validation_errors"])
        return {**state, "error_state": f"Analysis failed after {state['retry_count']} attempt(s): {detail}"}
    return state


def build_graph():
    g = StateGraph(AnalysisState)
    g.add_node("invoke_llm", invoke_llm)
    g.add_node("validate", validate)
    g.add_node("summarize", summarize)

    g.add_edge(START, "invoke_llm")
    g.add_edge("invoke_llm", "validate")
    g.add_conditional_edges(
        "validate",
        lambda state: "retry" if state["validation_errors"] and state["retry_count"] < settings.max_ai_retries else "summarize",
        {"retry": "invoke_llm", "summarize": "summarize"},
    )
    g.add_edge("summarize", END)

    return g.compile()


_graph = build_graph()


async def run_analysis(machine_summaries: list[dict]) -> AnalysisState:
    initial: AnalysisState = {
        "machine_summaries": machine_summaries,
        "valid_machine_ids": [m["machine_id"] for m in machine_summaries],
        "parsed_result": None,
        "validation_errors": [],
        "retry_count": 0,
        "error_state": None,
    }
    return await _graph.ainvoke(initial)
