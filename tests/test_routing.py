"""Tests for the deterministic route step (routing.py)."""

import pytest

from chat_quote_agent.routing import (
    BASELINE_FACTS,
    IMPLICIT_MAPPINGS,
    apply_implicit_mappings,
    map_implicit_code,
    match_condition,
    order_facts,
    parse_conditions,
    route,
    should_ignore_icd,
)


@pytest.mark.parametrize(
    ("icd", "expected"),
    [
        ("E11.9", "Type 2 Diabetes"),
        ("E11", "Type 2 Diabetes"),
        ("R73.09", "Type 2 Diabetes"),  # the R-code that routes to DM2
        ("E10", "Type 1 Diabetes"),
        ("E66.9", "BMI"),
        ("I10", "Hypertension"),
        ("R03.0", "Hypertension"),  # the R-code that routes to HTN
        ("E78.5", "Hyperlipidemia"),
        ("J45.9", "Asthma"),
        ("F41", "Anxiety"),
        ("E03.9", "Hypothyroid"),
        ("K21", "GERD"),
        ("I21", "Heart Attack"),
        ("I25.2", "Heart Attack"),
        ("G47.33", "OSA"),
        ("C61", "Prostate Cancer"),
        ("F90", "ADHD"),
    ],
)
def test_match_condition_known_codes(icd, expected):
    assert match_condition(icd).name == expected


@pytest.mark.parametrize("icd", ["Z99", "M25.5", "E78", "E78.6"])
def test_match_condition_unknown(icd):
    # E78 (no subcategory) and E78.6 (out of [0-5]) both miss Hyperlipidemia.
    assert match_condition(icd) is None


@pytest.mark.parametrize(
    ("icd", "expected"),
    [
        ("Z79", True),
        ("Z79.4", True),
        ("Z72.0", True),
        ("F17.2", True),
        ("Z87", True),
        ("F13.2", True),
        ("Z68", True),
        ("R99", True),
        ("R23.1", True),
        ("R73.09", False),
        ("R03.0", False),
        ("E11", False),
        ("I10", False),
    ],
)
def test_should_ignore_icd(icd, expected):
    assert should_ignore_icd(icd) is expected


def test_parse_conditions_empty():
    supported, unsupported, facts = parse_conditions([])
    assert supported == []
    assert unsupported == []
    assert facts == list(BASELINE_FACTS)


def test_parse_conditions_dm2():
    supported, unsupported, facts = parse_conditions(
        [{"icd_code": "E11.9", "name": "Type 2 Diabetes"}]
    )
    assert supported == ["Type 2 Diabetes"]
    assert unsupported == []
    assert facts == ["tobacco", "bmi", "age", "dm2", "labs"]


def test_parse_conditions_hypothyroid():
    supported, _, facts = parse_conditions(
        [{"icd_code": "E03.9", "name": "Hypothyroidism"}]
    )
    assert supported == ["Hypothyroid"]
    assert facts == ["tobacco", "bmi", "age", "hypothyroid", "labs-deps"]


def test_parse_conditions_unsupported():
    supported, unsupported, facts = parse_conditions(
        [{"icd_code": "M25.5", "name": "Arthritis"}]
    )
    assert supported == []
    assert unsupported == ["Arthritis"]
    assert facts == list(BASELINE_FACTS)


def test_parse_conditions_ignores_medication_codes():
    supported, unsupported, facts = parse_conditions(
        [{"icd_code": "Z79.4", "name": "Metformin"}]
    )
    assert supported == []
    assert unsupported == []
    assert facts == list(BASELINE_FACTS)


def test_parse_conditions_accepts_condition_key():
    # The prompt emits `name`; the pipeline's upstream emits `condition`.
    supported, _, _ = parse_conditions([{"icd_code": "J45", "condition": "Asthma"}])
    assert supported == ["Asthma"]


def test_parse_conditions_diabetes_drops_htn():
    supported, unsupported, facts = parse_conditions(
        [
            {"icd_code": "E11.9", "name": "Type 2 Diabetes"},
            {"icd_code": "I10", "name": "Hypertension"},
        ]
    )
    assert supported == ["Hypertension", "Type 2 Diabetes"]
    assert unsupported == []
    # htn folds into diabetes's cardiovascular rating, not rated separately.
    assert "htn" not in facts
    assert facts == ["tobacco", "bmi", "age", "dm2", "labs"]


def test_order_facts_baseline_first_then_alphabetical():
    assert order_facts(["labs", "age", "dm2", "tobacco", "osa"]) == [
        "tobacco",
        "age",
        "dm2",
        "labs",
        "osa",
    ]


def test_map_implicit_code():
    assert map_implicit_code("E14.9", IMPLICIT_MAPPINGS) == "E11"
    assert map_implicit_code("E11.9", IMPLICIT_MAPPINGS) == "E11.9"
    assert map_implicit_code("e14.9", IMPLICIT_MAPPINGS) == "E11"


def test_apply_implicit_mappings_mutates_in_place():
    conds = [{"icd_code": "E14.9", "name": "Diabetes"}]
    apply_implicit_mappings(conds, IMPLICIT_MAPPINGS)
    assert conds[0]["icd_code"] == "E11"


def test_route_node():
    result = route(
        {"summary": {"conditions": [{"icd_code": "E11.9", "name": "Type 2 Diabetes"}]}}
    )
    assert result == {
        "supported": ["Type 2 Diabetes"],
        "unsupported": [],
        "facts": ["tobacco", "bmi", "age", "dm2", "labs"],
    }


def test_route_node_applies_implicit_mapping():
    result = route(
        {"summary": {"conditions": [{"icd_code": "E14.9", "name": "Diabetes"}]}}
    )
    assert result["supported"] == ["Type 2 Diabetes"]
