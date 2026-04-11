"""Tests for Phase 3 postconditions: seed examination and inclusion recording."""
import pytest

from lib.postconditions import (
    check_all_seeds_examined,
    check_new_inclusions_recorded,
    _all_ids,
)


# --- check_all_seeds_examined ---


def test_seeds_examined_all_present():
    seeds = [{"id": "p1"}, {"id": "p2"}]
    log = [
        {"source_paper_id": "p1", "direction": "forward"},
        {"source_paper_id": "p1", "direction": "backward"},
        {"source_paper_id": "p2", "direction": "forward"},
        {"source_paper_id": "p2", "direction": "backward"},
    ]
    satisfied, failures = check_all_seeds_examined(seeds, log)
    assert satisfied is True
    assert failures == []


def test_seeds_examined_missing_backward():
    seeds = [{"id": "p1"}]
    log = [{"source_paper_id": "p1", "direction": "forward"}]
    satisfied, failures = check_all_seeds_examined(seeds, log)
    assert satisfied is False
    assert "backward" in failures[0]


def test_seeds_examined_terminal_leaf_exempt():
    """Paper discovered at max_depth should not be required to have snowball entries."""
    seeds = [{"id": "p1"}, {"id": "p2"}]
    log = [
        # p1 is a depth-0 seed, fully examined
        {"source_paper_id": "p1", "direction": "forward"},
        {"source_paper_id": "p1", "direction": "backward"},
        # p2 was discovered at depth 2 (= max_depth), making it a terminal leaf
        {"source_paper_id": "p1", "direction": "forward",
         "discovered_paper_id": "p2", "depth_level": 2, "already_known": False,
         "screening_decision": "include"},
    ]
    satisfied, failures = check_all_seeds_examined(seeds, log, max_depth=2)
    assert satisfied is True


def test_seeds_examined_depth0_always_checked():
    """Original seeds (not discovered via snowball) must always be checked."""
    seeds = [{"id": "p1"}]
    log = []  # no snowball entries at all
    satisfied, failures = check_all_seeds_examined(seeds, log, max_depth=2)
    assert satisfied is False
    assert "p1" in failures[0]


def test_seeds_examined_already_known_not_terminal():
    """Papers marked already_known at max_depth are NOT terminal leaves."""
    seeds = [{"id": "p1"}]
    log = [
        {"source_paper_id": "x", "direction": "forward",
         "discovered_paper_id": "p1", "depth_level": 2, "already_known": True,
         "screening_decision": None},
    ]
    # p1 is already_known at max_depth — it's not a new discovery, so not exempt
    satisfied, failures = check_all_seeds_examined(seeds, log, max_depth=2)
    assert satisfied is False


# --- check_new_inclusions_recorded ---


def test_inclusions_exact_id_match():
    log = [{"screening_decision": "include", "discovered_paper_id": "10.1000/abc"}]
    included = [{"id": "10.1000/abc"}]
    candidates = [{"id": "10.1000/abc"}]
    satisfied, failures = check_new_inclusions_recorded(log, included, candidates)
    assert satisfied is True


def test_inclusions_s2_to_doi_promotion():
    """discovered_paper_id is S2 hash, but included has DOI as id and S2 hash in s2_id."""
    log = [{"screening_decision": "include", "discovered_paper_id": "a007112e362d"}]
    included = [{"id": "10.1007/s11606-014-3141-1", "s2_id": "a007112e362d"}]
    candidates = [{"id": "10.1007/s11606-014-3141-1", "s2_id": "a007112e362d"}]
    satisfied, failures = check_new_inclusions_recorded(log, included, candidates)
    assert satisfied is True


def test_inclusions_arxiv_id_match():
    log = [{"screening_decision": "include", "discovered_paper_id": "2301.12345"}]
    included = [{"id": "10.48550/arXiv.2301.12345", "arxiv_id": "2301.12345"}]
    candidates = [{"id": "10.48550/arXiv.2301.12345", "arxiv_id": "2301.12345"}]
    satisfied, failures = check_new_inclusions_recorded(log, included, candidates)
    assert satisfied is True


def test_inclusions_genuinely_missing():
    log = [{"screening_decision": "include", "discovered_paper_id": "missing_paper"}]
    included = [{"id": "10.1000/other"}]
    candidates = [{"id": "10.1000/other"}]
    satisfied, failures = check_new_inclusions_recorded(log, included, candidates)
    assert satisfied is False
    assert "missing_paper" in failures[0]


def test_inclusions_skips_non_include_decisions():
    """Entries with screening_decision != 'include' should be ignored."""
    log = [
        {"screening_decision": "exclude", "discovered_paper_id": "excluded_paper"},
        {"screening_decision": None, "discovered_paper_id": "skipped"},
    ]
    satisfied, failures = check_new_inclusions_recorded(log, [], [])
    assert satisfied is True


# --- _all_ids helper ---


def test_all_ids_collects_all_fields():
    records = [{"id": "doi1", "s2_id": "s2a", "doi": "doi1", "arxiv_id": "ax1"}]
    ids = _all_ids(records)
    assert ids == {"doi1", "s2a", "ax1"}


def test_all_ids_skips_none_values():
    records = [{"id": "p1", "s2_id": None, "doi": None}]
    ids = _all_ids(records)
    assert ids == {"p1"}
