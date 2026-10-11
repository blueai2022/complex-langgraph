"""Tests for the graph state schema (state.py)."""

import pytest
from pydantic import ValidationError

from chat_quote_agent.state import FactorRating, FinalResult, GraphState


class TestFactorRating:
    def test_defaults(self):
        fr = FactorRating(kind="none")
        assert fr.kind == "none"
        assert fr.tier == ""
        assert fr.debits == 0
        assert fr.text == ""
        assert fr.smoking_status is False
        assert fr.is_juvenile is False
        assert fr.children == []
        assert fr.display_name == ""
        assert fr.display_text == ""
        assert fr.contribution == ""
        assert fr.explanation == ""

    def test_recursive_children(self):
        fr = FactorRating(kind="list", children=[FactorRating(kind="none")])
        assert fr.children[0].kind == "none"

    def test_kind_is_validated(self):
        with pytest.raises(ValidationError):
            FactorRating(kind="bogus")

    def test_children_default_is_not_shared(self):
        # The mutable-default trap: each instance gets its own list.
        a = FactorRating(kind="none")
        b = FactorRating(kind="none")
        a.children.append(FactorRating(kind="none"))
        assert b.children == []


class TestFinalResult:
    def test_defaults(self):
        fr = FinalResult()
        assert fr.final_rating == ""
        assert fr.declined == []
        assert fr.partition_scores == []
        assert fr.message == ""
        assert fr.explanations == {}

    def test_mutable_defaults_not_shared(self):
        a = FinalResult()
        b = FinalResult()
        a.declined.append("x")
        a.explanations["k"] = "v"
        assert b.declined == []
        assert b.explanations == {}


class TestGraphState:
    def test_empty_state_is_valid(self):
        # total=False: every field is optional.
        assert GraphState() == {}

    def test_partial_state_is_valid(self):
        s = GraphState(stage="creation", supported=["a"])
        assert s["stage"] == "creation"
        assert s["supported"] == ["a"]
