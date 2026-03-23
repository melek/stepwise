"""Tests for per-record validators and oracle contract wrappers."""

from lib.postconditions import validate_screening_criterion


def test_valid_criterion():
    record = {
        "criterion_id": "IC1",
        "criterion_type": "inclusion",
        "met": "yes",
        "evidence": "The abstract states: 'we formally verify...'",
        "source": "abstract",
    }
    ok, failures = validate_screening_criterion(record)
    assert ok is True
    assert failures == []


def test_invalid_met_value():
    record = {
        "criterion_id": "IC1",
        "criterion_type": "inclusion",
        "met": "maybe",
        "evidence": "some text",
        "source": "abstract",
    }
    ok, failures = validate_screening_criterion(record)
    assert ok is False
    assert any("met" in f for f in failures)


def test_empty_evidence():
    record = {
        "criterion_id": "IC1",
        "criterion_type": "inclusion",
        "met": "yes",
        "evidence": "",
        "source": "abstract",
    }
    ok, failures = validate_screening_criterion(record)
    assert ok is False
    assert any("evidence" in f for f in failures)


def test_invalid_criterion_id_pattern():
    record = {
        "criterion_id": "QA1",
        "criterion_type": "inclusion",
        "met": "yes",
        "evidence": "some text",
        "source": "abstract",
    }
    ok, failures = validate_screening_criterion(record)
    assert ok is False
    assert any("criterion_id" in f for f in failures)


def test_invalid_criterion_type():
    record = {
        "criterion_id": "IC1",
        "criterion_type": "quality",
        "met": "yes",
        "evidence": "some text",
        "source": "abstract",
    }
    ok, failures = validate_screening_criterion(record)
    assert ok is False
    assert any("criterion_type" in f for f in failures)


def test_invalid_source():
    record = {
        "criterion_id": "IC1",
        "criterion_type": "inclusion",
        "met": "yes",
        "evidence": "some text",
        "source": "google",
    }
    ok, failures = validate_screening_criterion(record)
    assert ok is False
    assert any("source" in f for f in failures)


from lib.postconditions import validate_screening_decision


def _make_criteria(ics, ecs):
    """Helper: build criteria_evaluations from IC/EC met values."""
    evals = []
    for i, met in enumerate(ics, 1):
        evals.append({"criterion_id": f"IC{i}", "criterion_type": "inclusion",
                       "met": met, "evidence": "text", "source": "abstract"})
    for i, met in enumerate(ecs, 1):
        evals.append({"criterion_id": f"EC{i}", "criterion_type": "exclusion",
                       "met": met, "evidence": "text", "source": "abstract"})
    return evals


def test_valid_include_decision():
    record = {
        "decision": "include",
        "criteria_evaluations": _make_criteria(["yes", "yes"], ["no"]),
        "reasoning": "All IC met, no EC triggered.",
    }
    ok, failures = validate_screening_decision(record)
    assert ok is True


def test_include_with_ec_met_fails():
    record = {
        "decision": "include",
        "criteria_evaluations": _make_criteria(["yes"], ["yes"]),
        "reasoning": "Included despite EC.",
    }
    ok, failures = validate_screening_decision(record)
    assert ok is False
    assert any("decision rule" in f.lower() or "biconditional" in f.lower() for f in failures)


def test_include_with_ic_not_met_fails():
    record = {
        "decision": "include",
        "criteria_evaluations": _make_criteria(["no", "yes"], ["no"]),
        "reasoning": "Included despite IC not met.",
    }
    ok, failures = validate_screening_decision(record)
    assert ok is False


def test_valid_exclude_ec_met():
    record = {
        "decision": "exclude",
        "criteria_evaluations": _make_criteria(["yes"], ["yes"]),
        "reasoning": "EC1 met.",
    }
    ok, failures = validate_screening_decision(record)
    assert ok is True


def test_valid_exclude_ic_not_met():
    record = {
        "decision": "exclude",
        "criteria_evaluations": _make_criteria(["no"], ["no"]),
        "reasoning": "IC1 not met.",
    }
    ok, failures = validate_screening_decision(record)
    assert ok is True


def test_exclude_with_all_ic_met_no_ec_fails():
    record = {
        "decision": "exclude",
        "criteria_evaluations": _make_criteria(["yes"], ["no"]),
        "reasoning": "Excluded anyway.",
    }
    ok, failures = validate_screening_decision(record)
    assert ok is False


def test_valid_flag_for_full_text():
    record = {
        "decision": "flag_for_full_text",
        "criteria_evaluations": _make_criteria(["yes", "unclear"], ["no"]),
        "reasoning": "IC2 unclear from abstract.",
    }
    ok, failures = validate_screening_decision(record)
    assert ok is True


def test_flag_with_ec_met_fails():
    record = {
        "decision": "flag_for_full_text",
        "criteria_evaluations": _make_criteria(["unclear"], ["yes"]),
        "reasoning": "Flagged despite EC met.",
    }
    ok, failures = validate_screening_decision(record)
    assert ok is False


def test_empty_criteria_fails():
    record = {
        "decision": "include",
        "criteria_evaluations": [],
        "reasoning": "No criteria.",
    }
    ok, failures = validate_screening_decision(record)
    assert ok is False


def test_empty_reasoning_fails():
    record = {
        "decision": "include",
        "criteria_evaluations": _make_criteria(["yes"], ["no"]),
        "reasoning": "",
    }
    ok, failures = validate_screening_decision(record)
    assert ok is False


from lib.postconditions import validate_extraction_field, validate_concept_record


# --- EXTRACT_FIELD ---

def test_valid_extraction_field():
    record = {"field_name": "methodology", "value": "randomized controlled trial",
              "confidence": "high", "source_location": "Section 3: Methods"}
    ok, failures = validate_extraction_field(record, parent_source="full_text")
    assert ok is True

def test_abstract_source_high_confidence_fails():
    record = {"field_name": "methodology", "value": "RCT", "confidence": "high",
              "source_location": "abstract"}
    ok, failures = validate_extraction_field(record, parent_source="abstract")
    assert ok is False
    assert any("confidence" in f for f in failures)

def test_abstract_source_medium_confidence_ok():
    record = {"field_name": "methodology", "value": "RCT", "confidence": "medium",
              "source_location": "abstract"}
    ok, failures = validate_extraction_field(record, parent_source="abstract")
    assert ok is True

def test_extraction_failed_value_ok():
    record = {"field_name": "methodology", "value": "extraction_failed",
              "confidence": "low", "source_location": "abstract"}
    ok, failures = validate_extraction_field(record, parent_source="abstract")
    assert ok is True

def test_empty_field_name_fails():
    record = {"field_name": "", "value": "something", "confidence": "medium",
              "source_location": "abstract"}
    ok, failures = validate_extraction_field(record, parent_source="full_text")
    assert ok is False

def test_invalid_confidence_fails():
    record = {"field_name": "methodology", "value": "something", "confidence": "very_high",
              "source_location": "Section 3"}
    ok, failures = validate_extraction_field(record, parent_source="full_text")
    assert ok is False

def test_empty_value_fails():
    record = {"field_name": "methodology", "value": "", "confidence": "medium",
              "source_location": "Section 3"}
    ok, failures = validate_extraction_field(record, parent_source="full_text")
    assert ok is False


# --- IDENTIFY_CONCEPTS ---

def test_valid_concept():
    record = {"concept_id": "formal-verification", "label": "Formal Verification",
              "definition": "The use of mathematical proofs to verify system correctness",
              "frequency": 3}
    ok, failures = validate_concept_record(record)
    assert ok is True

def test_single_char_concept_id_fails():
    record = {"concept_id": "x", "label": "X",
              "definition": "Some concept with a single character ID", "frequency": 1}
    ok, failures = validate_concept_record(record)
    assert ok is False
    assert any("concept_id" in f for f in failures)

def test_short_definition_fails():
    record = {"concept_id": "formal-verification", "label": "Formal Verification",
              "definition": "Proofs", "frequency": 1}
    ok, failures = validate_concept_record(record)
    assert ok is False
    assert any("definition" in f for f in failures)

def test_zero_frequency_fails():
    record = {"concept_id": "formal-verification", "label": "Formal Verification",
              "definition": "The use of mathematical proofs to verify system correctness",
              "frequency": 0}
    ok, failures = validate_concept_record(record)
    assert ok is False

def test_concept_id_with_uppercase_fails():
    record = {"concept_id": "Formal-Verification", "label": "Formal Verification",
              "definition": "The use of mathematical proofs to verify system correctness",
              "frequency": 1}
    ok, failures = validate_concept_record(record)
    assert ok is False


from lib.oracle_contracts import (
    OracleContract,
    SCREEN_CRITERION,
    SCREEN_DECISION,
    EXTRACT_FIELD,
    IDENTIFY_CONCEPTS,
    validate_and_recover,
)


def test_contract_registry_names():
    assert SCREEN_CRITERION.contract_id == "SCREEN_CRITERION"
    assert SCREEN_DECISION.contract_id == "SCREEN_DECISION"
    assert EXTRACT_FIELD.contract_id == "EXTRACT_FIELD"
    assert IDENTIFY_CONCEPTS.contract_id == "IDENTIFY_CONCEPTS"


def test_validate_and_recover_pass():
    record = {
        "criterion_id": "IC1", "criterion_type": "inclusion",
        "met": "yes", "evidence": "The abstract states formal verification.",
        "source": "abstract",
    }
    result = validate_and_recover(record, SCREEN_CRITERION)
    assert result["validation"]["satisfied"] is True
    assert result["validation"]["recovery_applied"] is False
    assert result["record"]["_validated_by"]["contract_id"] == "SCREEN_CRITERION"
    assert result["record"]["_validated_by"]["satisfied"] is True


def test_validate_and_recover_fail_with_recovery():
    record = {
        "criterion_id": "IC1", "criterion_type": "inclusion",
        "met": "maybe",  # invalid
        "evidence": "some text", "source": "abstract",
    }
    result = validate_and_recover(record, SCREEN_CRITERION)
    recovered = result["record"]
    assert recovered["met"] == "unclear"
    assert "validation_failed" in recovered["evidence"]
    assert recovered["recovery_applied"] is True
    assert result["validation"]["satisfied"] is False
    assert result["validation"]["recovery_applied"] is True


def test_provenance_metadata_on_record():
    record = {
        "criterion_id": "IC1", "criterion_type": "inclusion",
        "met": "yes", "evidence": "text", "source": "abstract",
    }
    result = validate_and_recover(record, SCREEN_CRITERION)
    prov = result["record"]["_validated_by"]
    assert prov["contract_id"] == "SCREEN_CRITERION"
    assert "timestamp" in prov
    assert isinstance(prov["satisfied"], bool)


def test_screen_decision_recovery_excludes():
    record = {
        "decision": "include",
        "criteria_evaluations": [
            {"criterion_id": "IC1", "criterion_type": "inclusion",
             "met": "yes", "evidence": "text", "source": "abstract"},
            {"criterion_id": "EC1", "criterion_type": "exclusion",
             "met": "yes", "evidence": "text", "source": "abstract"},
        ],
        "reasoning": "Included despite EC.",
    }
    result = validate_and_recover(record, SCREEN_DECISION)
    assert result["validation"]["satisfied"] is False
    assert result["record"]["decision"] == "exclude"
    assert "decision_rule_violation" in result["record"]["reasoning"]


def test_extract_field_default_parent_source():
    """EXTRACT_FIELD has validator_kwargs default for parent_source."""
    record = {"field_name": "methodology", "value": "RCT",
              "confidence": "high", "source_location": "Section 3"}
    result = validate_and_recover(record, EXTRACT_FIELD)
    # Default parent_source is full_text, so high confidence is allowed
    assert result["validation"]["satisfied"] is True


def test_extract_field_override_parent_source():
    """Caller can override parent_source."""
    record = {"field_name": "methodology", "value": "RCT",
              "confidence": "high", "source_location": "abstract"}
    result = validate_and_recover(record, EXTRACT_FIELD, parent_source="abstract")
    assert result["validation"]["satisfied"] is False
    recovered = result["record"]
    assert recovered["value"] == "extraction_failed"
    assert recovered["confidence"] == "low"


from lib.postconditions import validate_synthesis_claims


def test_valid_synthesis_paragraph():
    paragraphs = [
        {"text": "Formal verification improves reliability [@dijkstra1968].", "section": "3.2"},
    ]
    included_keys = {"dijkstra1968", "leino2010"}
    extraction_completeness = {"dijkstra1968": 1.0, "leino2010": 0.8}
    ok, failures = validate_synthesis_claims(paragraphs, included_keys, extraction_completeness)
    assert ok is True


def test_paragraph_without_citation_fails():
    paragraphs = [
        {"text": "Formal verification improves reliability.", "section": "3.2"},
    ]
    ok, failures = validate_synthesis_claims(paragraphs, set(), {})
    assert ok is False
    assert any("citation" in f.lower() for f in failures)


def test_citation_to_absent_paper_fails():
    paragraphs = [
        {"text": "Results show improvement [@ghost2099].", "section": "3.2"},
    ]
    included_keys = {"dijkstra1968"}
    ok, failures = validate_synthesis_claims(paragraphs, included_keys, {})
    assert ok is False
    assert any("ghost2099" in f for f in failures)


def test_low_completeness_paper_without_qualification_fails():
    paragraphs = [
        {"text": "The paper found strong results [@baddata2024].", "section": "3.2"},
    ]
    included_keys = {"baddata2024"}
    extraction_completeness = {"baddata2024": 0.3}
    ok, failures = validate_synthesis_claims(paragraphs, included_keys, extraction_completeness)
    assert ok is False
    assert any("qualification" in f.lower() or "completeness" in f.lower() for f in failures)


def test_low_completeness_with_qualification_passes():
    paragraphs = [
        {"text": "The paper found results [limited data] [@baddata2024].", "section": "3.2"},
    ]
    included_keys = {"baddata2024"}
    extraction_completeness = {"baddata2024": 0.3}
    ok, failures = validate_synthesis_claims(paragraphs, included_keys, extraction_completeness)
    assert ok is True
