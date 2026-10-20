"""Regression tests for postcondition false failures (#17, #25, #26, #27, #28).

Each test reproduces a failure reported from a real run, where the check
rejected correct work, plus the guard that keeps the check meaningful.
"""
from fractions import Fraction

from lib.postconditions import (
    canonical_key,
    check_all_seeds_examined,
    check_minimum_metadata,
    check_new_inclusions_recorded,
    validate_extraction_field,
)
from lib.saturation import discovery_saturation


# --- #17: canonical-ID drift between snowball log and included.jsonl ---


def test_canonical_key_strips_scheme_prefixes():
    assert canonical_key("s2:D287133A") == canonical_key("d287133a")
    assert canonical_key("doi:10.1007/S11606-014-3141-1") == canonical_key("10.1007/s11606-014-3141-1")
    assert canonical_key("https://doi.org/10.1/X") == canonical_key("10.1/x")
    assert canonical_key("arxiv:2301.01234v2") == canonical_key("2301.01234")


def test_canonical_key_keeps_pmid_scheme():
    # `pmid:` is the canonical form the search runbook writes; a bare number
    # must not be confused with it.
    assert canonical_key("pmid:123") != canonical_key("123")


def test_inclusion_recorded_matches_prefixed_s2_against_bare_s2_id():
    """The exact shape from the reopened #17: log has `s2:<hash>`, the
    included record has a `doi:` id and a bare `s2_id`."""
    rec = {"id": "doi:10.1000/abc", "s2_id": "d287133a0b9b9efbce065af0ae5f687021b395e3"}
    log = [{"discovered_paper_id": "s2:d287133a0b9b9efbce065af0ae5f687021b395e3",
            "screening_decision": "include"}]
    ok, failures = check_new_inclusions_recorded(log, [rec], [rec])
    assert ok, failures


def test_inclusion_still_fails_when_paper_truly_missing():
    log = [{"discovered_paper_id": "s2:ffff", "screening_decision": "include"}]
    ok, failures = check_new_inclusions_recorded(log, [], [])
    assert not ok and len(failures) == 2


# --- #27: depth-aware seed set ---


def _both(src, depth=1):
    return [
        {"source_paper_id": src, "direction": "forward", "depth_level": depth},
        {"source_paper_id": src, "direction": "backward", "depth_level": depth},
    ]


def test_terminal_leaf_exempt_despite_id_drift():
    """A depth-max discovery logged under its S2 id, then written to
    included.jsonl under a promoted DOI, is still a terminal leaf."""
    seeds = [
        {"id": "p1"},
        {"id": "doi:10.1/leaf", "s2_id": "abc123"},
    ]
    log = _both("p1") + [
        {"source_paper_id": "p1", "direction": "forward", "depth_level": 1,
         "discovered_paper_id": "s2:abc123", "already_known": False,
         "screening_decision": "include"},
    ]
    ok, failures = check_all_seeds_examined(seeds, log, max_depth=1)
    assert ok, failures


def test_seed_examined_under_a_different_id_form():
    seeds = [{"id": "doi:10.1/seed", "s2_id": "abc123"}]
    log = _both("s2:abc123")
    ok, failures = check_all_seeds_examined(seeds, log, max_depth=2)
    assert ok, failures


def test_saturation_stop_before_max_depth_makes_last_level_terminal():
    """Snowballing stopped on saturation at depth 1 of max 3: depth-1
    discoveries were never snowballed and must not be required to be."""
    seeds = [{"id": "p1"}, {"id": "p2"}]
    log = _both("p1") + [
        {"source_paper_id": "p1", "direction": "backward", "depth_level": 1,
         "discovered_paper_id": "p2", "already_known": False,
         "screening_decision": "include"},
    ]
    ok, failures = check_all_seeds_examined(seeds, log, max_depth=3)
    assert ok, failures


def test_intermediate_depth_discoveries_still_checked():
    """Depth-1 discoveries are seeds for depth 2 when depth 2 ran."""
    seeds = [{"id": "p1"}, {"id": "p2"}]
    log = _both("p1") + [
        {"source_paper_id": "p1", "direction": "backward", "depth_level": 1,
         "discovered_paper_id": "p2", "already_known": False,
         "screening_decision": "include"},
        {"source_paper_id": "p9", "direction": "forward", "depth_level": 2},
    ]
    ok, failures = check_all_seeds_examined(seeds, log, max_depth=3)
    assert not ok
    assert any("p2" in f for f in failures)


# --- #26: empty-direction sentinel entries ---


def _sentinel(src, direction, depth=1):
    return {"source_paper_id": src, "direction": direction,
            "discovered_paper_id": None, "already_known": None,
            "screening_decision": None, "depth_level": depth,
            "note": "empty_array_from_api"}


def test_sentinel_counts_as_examined_direction():
    seeds = [{"id": "p1"}]
    log = [{"source_paper_id": "p1", "direction": "backward", "depth_level": 1,
            "discovered_paper_id": "x", "already_known": True},
           _sentinel("p1", "forward")]
    ok, failures = check_all_seeds_examined(seeds, log, max_depth=2)
    assert ok, failures


def test_sentinel_excluded_from_saturation_denominator():
    log = [
        {"depth_level": 1, "discovered_paper_id": "a", "screening_decision": "include", "already_known": False},
        {"depth_level": 1, "discovered_paper_id": "b", "screening_decision": "exclude", "already_known": False},
        _sentinel("p1", "forward"),
        _sentinel("p1", "backward"),
    ]
    assert discovery_saturation(log, 1) == Fraction(1, 2)


def test_saturation_denominator_excludes_already_known():
    """Canonical definition: newly included / newly examined."""
    log = [
        {"depth_level": 1, "discovered_paper_id": "a", "screening_decision": "include", "already_known": False},
        {"depth_level": 1, "discovered_paper_id": "b", "screening_decision": "exclude", "already_known": False},
        {"depth_level": 1, "discovered_paper_id": "c", "screening_decision": None, "already_known": True},
    ]
    assert discovery_saturation(log, 1) == Fraction(1, 2)


# --- #28: metadata fields keep high confidence on abstract-only records ---


def test_metadata_field_high_confidence_ok_on_abstract_record():
    rec = {"field_name": "year", "value": "2021", "source_location": "metadata",
           "confidence": "high"}
    ok, failures = validate_extraction_field(rec, parent_source="abstract")
    assert ok, failures


def test_content_field_high_confidence_still_rejected_on_abstract_record():
    rec = {"field_name": "framework_used", "value": "STPA", "source_location": "abstract",
           "confidence": "high"}
    ok, failures = validate_extraction_field(rec, parent_source="abstract")
    assert not ok


# --- #25: abstracts the source API doesn't provide ---


def _cand(i, abstract="An abstract.", gap=None):
    c = {"id": f"p{i}", "title": "T", "abstract": abstract, "authors": ["A"], "year": 2020}
    if gap is not None:
        c["metadata_gap"] = gap
    return c


def test_tagged_missing_abstract_passes():
    cands = [_cand(i) for i in range(9)] + [_cand(9, abstract=None, gap=["abstract"])]
    ok, failures = check_minimum_metadata(cands)
    assert ok, failures


def test_untagged_missing_abstract_fails():
    cands = [_cand(0), _cand(1, abstract="")]
    ok, failures = check_minimum_metadata(cands)
    assert not ok
    assert "p1" in failures[0] and "abstract" in failures[0]


def test_missing_abstracts_over_threshold_fail_as_systemic():
    cands = [_cand(i) for i in range(2)] + [_cand(i, abstract=None, gap=["abstract"]) for i in range(2, 4)]
    ok, failures = check_minimum_metadata(cands)
    assert not ok
    assert any("abstract" in f and "%" in f for f in failures)


def test_missing_abstracts_at_threshold_pass():
    cands = [_cand(i) for i in range(3)] + [_cand(3, abstract=None, gap=["abstract"])]
    ok, failures = check_minimum_metadata(cands)
    assert ok, failures


def test_gap_tag_does_not_excuse_other_fields():
    c = _cand(0, abstract=None, gap=["abstract"])
    c["title"] = None
    ok, failures = check_minimum_metadata([c] + [_cand(i) for i in range(1, 8)])
    assert not ok and "title" in failures[0]


# --- schema drift: a record without its ID field is reported, never raised ---


def test_checks_report_records_missing_id_instead_of_crashing():
    from lib.postconditions import (
        check_all_candidates_screened, check_all_papers_extracted,
        check_included_consistency, check_no_duplicate_ids, check_no_orphan_inclusions,
    )
    drifted = {"paper_id": "p1", "title": "Drifted"}
    for check, args in [
        (check_all_candidates_screened, ([drifted], [])),
        (check_included_consistency, ([drifted], [])),
        (check_no_orphan_inclusions, ([drifted], [])),
        (check_all_papers_extracted, ([drifted], [])),
        (check_all_seeds_examined, ([drifted], [])),
    ]:
        ok, failures = check(*args)
        assert not ok and "no 'id' field" in failures[0] and "Drifted" in failures[0], check.__name__
    assert check_no_duplicate_ids([drifted])[0]  # left to check_minimum_metadata
    ok, failures = check_new_inclusions_recorded([{"screening_decision": "include"}], [], [])
    assert not ok and "discovered_paper_id" in failures[0]
