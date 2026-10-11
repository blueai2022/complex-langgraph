"""The chat-quote main-flow graph."""

from __future__ import annotations

from typing import Any

from langgraph.graph import END, START, StateGraph
from langgraph.checkpoint.memory import MemorySaver
from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer

from .routing import route
from .state import GraphState


def build_main_graph():
    graph = StateGraph(GraphState)

    # --- nodes ---

    # medical_summary (LLM tool): text -> conditions list
    def medical_summary(state: GraphState) -> dict[str, Any]:
        return {}

    # specialists: the fact extraction loop (extract -> publish)
    def consult(state: GraphState) -> dict[str, Any]:
        return {}

    # specialists: Rate<Fact> -> FactorRating
    def rate(state: GraphState) -> dict[str, Any]:
        return {}

    # final-decision: partitions -> calc -> message + explanations
    def final_decision(state: GraphState) -> dict[str, Any]:
        return {}

    # main agent: relay the message (a question, or the final assessment)
    def respond(state: GraphState) -> dict[str, Any]:
        return {}

    # protect/stop: compose the stop message and end the turn for human review.
    # All three guards converge here, so the message lives in exactly one place.
    def protect(state: GraphState) -> dict[str, Any]:
        return {}

    graph.add_node("medical_summary", medical_summary)
    graph.add_node("route", route)
    graph.add_node("consult", consult)
    graph.add_node("rate", rate)
    graph.add_node("final_decision", final_decision)
    graph.add_node("respond", respond)
    graph.add_node("protect", protect)

    # --- guard routers (read state, return the next node) ---

    def guard_follow_up(state: GraphState) -> str:
        # GUARD 1 · follow-up guard — fires only when the user is answering a
        # follow-up question (stage == "question"). The LLM flags off-scent and
        # conflict count (plus multiple-people); code derives the action:
        # off-scent & >2 conflicts, or multiple-people -> protect.
        # TODO(follow-up-guard): read the review signals and return "protect".
        return "medical_summary"

    def guard_overwatch(state: GraphState) -> str:
        # GUARD 2 · overwatch reviewer (action-stop) — after medical_summary,
        # before route. Grades objectives + scenario matches; code finalizes.
        # final_action == ActionStop -> protect.
        # TODO(overwatch-reviewer): read the resolved outcome and return "protect".
        return "route"

    def guard_value_norm(state: GraphState) -> str:
        # GUARD 3 · value-norm probe (pre-fact gate) — between route and
        # consult, on the raw conversation text. probe -> protect;
        # questions -> ask (respond); clean -> consult.
        # TODO(value-norm): read the gate outcome and route accordingly.
        return "consult"

    # --- edges ---

    # turn start -> follow-up guard (protect | medical_summary)
    graph.add_conditional_edges(
        START,
        guard_follow_up,
        {"medical_summary": "medical_summary", "protect": "protect"},
    )
    # medical_summary -> overwatch reviewer (route | protect)
    graph.add_conditional_edges(
        "medical_summary",
        guard_overwatch,
        {"route": "route", "protect": "protect"},
    )
    # route -> value-norm probe (consult | respond | protect)
    graph.add_conditional_edges(
        "route",
        guard_value_norm,
        {"consult": "consult", "respond": "respond", "protect": "protect"},
    )

    # consult -> rate -> final_decision -> respond -> END
    graph.add_edge("consult", "rate")
    graph.add_edge("rate", "final_decision")
    graph.add_edge("final_decision", "respond")
    graph.add_edge("respond", END)
    graph.add_edge("protect", END)

    # TODO(main-flow): missing-field check after consult -> respond (ask)
    # TODO(main-flow): check_more_info gate (last-check) -> re-enter medical_summary (YES) | rate (NO)

    serde = JsonPlusSerializer(
        allowed_msgpack_modules=[
            ("chat_quote_agent.state", "FactorRating"),
            ("chat_quote_agent.state", "FinalResult"),
        ]
    )
    return graph.compile(checkpointer=MemorySaver(serde=serde))


if __name__ == "__main__":
    print(build_main_graph().get_graph().draw_mermaid())
