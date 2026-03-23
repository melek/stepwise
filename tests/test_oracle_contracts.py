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
