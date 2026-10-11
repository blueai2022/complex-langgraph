"""The deterministic `route` step (langgraph-routing).

``summary -> conditions -> facts -> partitions``.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from .state import GraphState


@dataclass(frozen=True)
class Condition:
    """One row of the condition table."""

    name: str
    icd_regex: str            # raw regex, prefix-anchored at match time (e.g. "E11|R73\\.09")
    fact_ids: tuple[str, ...] # facts that rate this condition
    partition: str            # "" = no explicit partition

    def matches(self, icd: str) -> bool:
        return re.match(r"^(?:" + self.icd_regex + r")", icd) is not None


# The condition table - ICD prefixes, FactIDs, and partitions
# TODO: move this to config.
CONDITIONS: tuple[Condition, ...] = (
    Condition("Type 2 Diabetes", r"E11|R73\.09", ("dm2", "labs", "age", "bmi"), "Cardiovascular"),
    Condition("Type 1 Diabetes", r"E10", ("dm1", "labs", "age", "bmi"), "Cardiovascular"),
    Condition("BMI", r"E66", ("bmi",), "Cardiovascular"),
    Condition("Hypertension", r"I10|R03\.0", ("htn",), ""),
    Condition("Hyperlipidemia", r"E78\.[0-5]", ("hld",), ""),
    Condition("Asthma", r"J45", ("asthma",), ""),
    Condition("Anxiety", r"F41", ("anxiety",), ""),
    Condition("Hypothyroid", r"E03", ("hypothyroid", "labs-deps"), ""),
    Condition("GERD", r"K21", ("gerd",), ""),
    Condition("Heart Attack", r"I21|I22|I25\.2", ("heart_attack",), "Heart Attack"),
    Condition("OSA", r"G47\.33|G47\.30", ("osa",), ""),
    Condition("Prostate Cancer", r"C61|D07\.5|N42\.31|Z85\.46", ("prostate",), ""),
    Condition("ADHD", r"F90", ("adhd", "emotional_disorder"), ""),
)

# Facts always consulted first, before any condition-specific fact.
BASELINE_FACTS: tuple[str, ...] = ("tobacco", "bmi", "age")

# shouldIgnoreICD: codes the medical_summary emits that do NOT
# route to a fact (medication/status codes and bare R-codes), except the two
# R-codes that DO route (R73.09 -> DM2, R03.0 -> HTN).
_IGNORE_ICD_RE = re.compile(r"^(?:Z79|Z72\.0|F17\.2|Z87|F13\.2|Z68)")
_R_CODE_RE = re.compile(r"^R\d{2}(?:\.\d{1,2})?$")
_EXCLUDED_R_CODES = {"R73.09", "R03.0"}


def should_ignore_icd(icd: str) -> bool:
    u = icd.upper().strip()
    if u in _EXCLUDED_R_CODES:
        return False
    if _IGNORE_ICD_RE.match(u) or _R_CODE_RE.match(u):
        return True
    return False


def match_condition(icd: str) -> Condition | None:
    """The first condition whose ICD regex matches the code, else None."""
    u = icd.upper().strip()
    for cond in CONDITIONS:
        if cond.matches(u):
            return cond
    return None


def parse_conditions(
    summary_conditions: list[dict[str, Any]],
) -> tuple[list[str], list[str], list[str]]:
    """Match summary conditions to the table -> (supported, unsupported, factIDs)."""
    fact_set: set[str] = set()
    support_set: set[str] = set()
    unsupport_set: set[str] = set()

    for entry in summary_conditions:
        icd = str(entry.get("icd_code") or "").strip()
        # The prompt emits `name`; ParseConditions' upstream emits `condition`
        # Accept either.
        name = str(entry.get("condition") or entry.get("name") or "")
        if icd == "":
            continue
        if should_ignore_icd(icd):
            continue
        cond = match_condition(icd)
        if cond is not None:
            support_set.add(cond.name)
            fact_set.update(cond.fact_ids)
        elif name != "":
            unsupport_set.add(name)

    for bf in BASELINE_FACTS:
        fact_set.add(bf)

    # dm2/dm1 ⇒ drop htn/hld: diabetes owns the cardiovascular
    # rating; hypertension/hyperlipidemia are not rated separately.
    if "dm2" in fact_set or "dm1" in fact_set:
        fact_set.discard("htn")
        fact_set.discard("hld")

    # Returns supported/unsupported; sort for determinism.
    return sorted(support_set), sorted(unsupport_set), order_facts(list(fact_set))


_BASELINE_ORDER = {"tobacco": 0, "bmi": 1, "age": 2}


def order_facts(facts: list[str]) -> list[str]:
    """Baseline first (tobacco, bmi, age), then the rest alphabetically."""
    return sorted(facts, key=lambda f: (_BASELINE_ORDER.get(f, 3), f))


# Implicit ICD mapping: qualifier-less -> default rewrite,
# applied in chat mode before routing. Data lives in rules/implicit-icd-mapping.json.
@dataclass(frozen=True)
class ImplicitMapping:
    from_code: str
    to_code: str
    reason: str


IMPLICIT_MAPPINGS: tuple[ImplicitMapping, ...] = (
    ImplicitMapping("E14", "E11", "Unspecified diabetes defaults to Type 2"),
)


def map_implicit_code(code: str, mappings: tuple[ImplicitMapping, ...]) -> str:
    u = code.upper().strip()
    for m in mappings:
        if u.startswith(m.from_code.upper()):
            return m.to_code
    return code


def apply_implicit_mappings(
    conditions: list[dict[str, Any]], mappings: tuple[ImplicitMapping, ...]
) -> None:
    if not mappings:
        return
    for c in conditions:
        icd = str(c.get("icd_code") or "")
        if icd == "":
            continue
        c["icd_code"] = map_implicit_code(icd, mappings)


def route(state: GraphState) -> dict[str, Any]:
    """The `route` node: summary -> (supported, unsupported, facts)."""
    summary = state.get("summary") or {}
    raw = summary.get("conditions") or []
    conditions = [c for c in raw if isinstance(c, dict)]
    apply_implicit_mappings(conditions, IMPLICIT_MAPPINGS)
    supported, unsupported, facts = parse_conditions(conditions)
    return {"supported": supported, "unsupported": unsupported, "facts": facts}
