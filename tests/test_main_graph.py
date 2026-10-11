"""Tests for the main-flow graph (main_graph.py)."""

from langchain_core.messages import HumanMessage

from chat_quote_agent.main_graph import build_main_graph

EXPECTED_NODES = {
    "medical_summary",
    "route",
    "consult",
    "rate",
    "final_decision",
    "respond",
    "protect",
}


def test_build_main_graph_registers_all_nodes():
    app = build_main_graph()
    nodes = set(app.get_graph().nodes.keys())
    assert EXPECTED_NODES <= nodes


def test_build_main_graph_runs_end_to_end():
    app = build_main_graph()
    cfg = {"configurable": {"thread_id": "t1"}}
    result = app.invoke({"messages": [HumanMessage(content="Client has DM2")]}, cfg)
    # The stub medical_summary produces no summary, so route collects only the
    # baseline facts.
    assert result["facts"] == ["tobacco", "bmi", "age"]
    assert [type(m).__name__ for m in result["messages"]] == ["HumanMessage"]
