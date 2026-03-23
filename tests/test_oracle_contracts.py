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
