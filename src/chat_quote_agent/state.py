"""Graph state schema for the chat-quote main flow."""

from __future__ import annotations

from typing import Annotated, Any, TypedDict, Literal

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages
from pydantic import BaseModel, Field

class FactorRating(BaseModel): # exchanged between main agent and tools
    """The rating a fact's `rate` tool produces."""

    kind: Literal["none", "string", "numeric", "list"]   # always set — required
    tier: str = ""
    debits: int = 0
    text: str = ""
    smoking_status: bool = False
    is_juvenile: bool = False
    children: list["FactorRating"] = Field(default_factory=list) # sub-ratings (e.g. tobacco cigar/chewing)
    display_name: str = ""
    display_text: str = ""
    contribution: str = ""
    explanation: str = ""

FactorRating.model_rebuild()

class FinalResult(BaseModel):
    """The final_decision tool's output."""

    final_rating: str = ""
    declined: list[str] = Field(default_factory=list)
    partition_scores: list[dict[str, Any]] = Field(default_factory=list)
    message: str = ""
    explanations: dict[str, str] = Field(default_factory=dict)


class GraphState(TypedDict, total=False):
    """Shared graph state. ``total=False`` lets nodes write fields incrementally."""

    messages: Annotated[list[BaseMessage], add_messages]
    summary: dict[str, Any] | None

    # route: conditions -> supported/unsupported/facts
    supported: list[str]        # matched condition names
    unsupported: list[str]      # named conditions with no matching ICD
    facts: list[str]            # the ordered fact IDs to consult

    # consult + rate: facts -> FactorRating records
    decisions: dict[str, FactorRating]
    missing: list[str]          # missing-field gaps a follow-up must answer

    # finite state management (main agent)
    stage: Literal["creation", "question", "more_info", "last_check", "results", "post_results"]

    # final_decision (tool): decisions -> final rating + message + explanations
    final_result: FinalResult | None
