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

    # main agent: relay the final message
    def respond(state: GraphState) -> dict[str, Any]:
        return {}

    graph.add_node("medical_summary", medical_summary)
    graph.add_node("route", route)
    graph.add_node("consult", consult)
    graph.add_node("rate", rate)
    graph.add_node("final_decision", final_decision)
    graph.add_node("respond", respond)

    # happy path
    graph.add_edge(START, "medical_summary")
    graph.add_edge("medical_summary", "route")
    graph.add_edge("route", "consult")
    graph.add_edge("consult", "rate")
    graph.add_edge("rate", "final_decision")
    graph.add_edge("final_decision", "respond")
    graph.add_edge("respond", END)

    # TODO(value-normalize): gate between route and consult
    #   probe -> END (protect/human review); questions -> respond (ask)
    # TODO(main-flow): missing-field check after consult -> respond (ask)
    # TODO(main-flow): check_more_info gate -> re-enter medical_summary (YES) | rate (NO)
    # TODO(main-flow): follow-up guard at turn start -> END (protect)

    serde = JsonPlusSerializer(
        allowed_msgpack_modules=[
            ("chat_quote_agent.state", "FactorRating"),
            ("chat_quote_agent.state", "FinalResult"),
        ]
    )
    return graph.compile(checkpointer=MemorySaver(serde=serde))


if __name__ == "__main__":
    print(build_main_graph().get_graph().draw_mermaid())
