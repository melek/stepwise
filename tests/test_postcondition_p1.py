"""Tests for Phase 1 postcondition: count-based query matching."""
import pytest

from lib.postconditions import (
    normalize_database,
    check_query_counts_per_database,
    check_phase1_all,
)


def test_normalize_database_canonical():
    assert normalize_database("Semantic Scholar") == "semantic_scholar"
    assert normalize_database("arXiv") == "arxiv"
    assert normalize_database("PubMed") == "pubmed"
    assert normalize_database("semantic_scholar") == "semantic_scholar"


def test_normalize_database_unknown():
    assert normalize_database("Some New DB") == "some_new_db"


def test_check_query_counts_match():
    protocol = [
        {"database": "semantic_scholar", "query": "q1"},
        {"database": "semantic_scholar", "query": "q2"},
        {"database": "arxiv", "query": "q3"},
    ]
    log = [
        {"database": "semantic_scholar", "query": "transformed q1"},
        {"database": "semantic_scholar", "query": "transformed q2"},
        {"database": "arxiv", "query": "q3"},
    ]
    satisfied, failures = check_query_counts_per_database(protocol, log)
    assert satisfied is True
    assert failures == []


def test_check_query_counts_surplus_ok():
    """More log entries than protocol queries is fine."""
    protocol = [{"database": "semantic_scholar", "query": "q1"}]
    log = [
        {"database": "semantic_scholar", "query": "q1"},
        {"database": "semantic_scholar", "query": "bonus"},
    ]
    satisfied, failures = check_query_counts_per_database(protocol, log)
    assert satisfied is True


def test_check_query_counts_deficit_fails():
    protocol = [
        {"database": "semantic_scholar", "query": "q1"},
        {"database": "semantic_scholar", "query": "q2"},
        {"database": "semantic_scholar", "query": "q3"},
    ]
    log = [
        {"database": "semantic_scholar", "query": "q1"},
    ]
    satisfied, failures = check_query_counts_per_database(protocol, log)
    assert satisfied is False
    assert len(failures) == 1
    assert "expected >= 3" in failures[0]
    assert "found 1" in failures[0]


def test_check_query_counts_db_normalization():
    """Mixed naming conventions should still match via normalization."""
    protocol = [
        {"database": "Semantic Scholar", "query": "q1"},
        {"database": "arXiv", "query": "q2"},
    ]
    log = [
        {"database": "semantic_scholar", "query": "transformed"},
        {"database": "arxiv", "query": "also transformed"},
    ]
    satisfied, failures = check_query_counts_per_database(protocol, log)
    assert satisfied is True


def test_check_query_counts_missing_db():
    """Protocol specifies a database with no log entries at all."""
    protocol = [{"database": "pubmed", "query": "q1"}]
    log = [{"database": "semantic_scholar", "query": "q1"}]
    satisfied, failures = check_query_counts_per_database(protocol, log)
    assert satisfied is False
    assert "pubmed" in failures[0]


def test_check_query_counts_empty_log():
    protocol = [{"database": "semantic_scholar", "query": "q1"}]
    satisfied, failures = check_query_counts_per_database(protocol, [])
    assert satisfied is False


def test_check_query_counts_empty_protocol():
    """No protocol queries means nothing to check — should pass."""
    satisfied, failures = check_query_counts_per_database([], [{"database": "x", "query": "y"}])
    assert satisfied is True


def test_check_phase1_all_integration():
    """End-to-end: protocol queries + search log + candidates."""
    protocol_queries = [
        {"database": "semantic_scholar", "query": "q1"},
        {"database": "arxiv", "query": "q2"},
    ]
    search_log = [
        {"database": "semantic_scholar", "query": "transformed q1"},
        {"database": "arxiv", "query": "q2"},
    ]
    candidates = [
        {"id": "p1", "title": "Paper 1", "abstract": "abs", "authors": ["A"], "year": 2024},
        {"id": "p2", "title": "Paper 2", "abstract": "abs", "authors": ["B"], "year": 2023},
    ]
    satisfied, failures = check_phase1_all(protocol_queries, search_log, candidates)
    assert satisfied is True
    assert failures == []
