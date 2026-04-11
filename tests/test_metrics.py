"""Tests for lib/metrics.py — pure counting functions."""
import pytest

from lib.metrics import (
    count_excluded,
    count_flagged,
    count_included,
    count_candidates,
    max_snowball_depth,
    count_concepts,
    count_extractions,
    recompute_all,
)


# --- count_excluded ---

class TestCountExcluded:
    def test_basic(self):
        log = [
            {"decision": "exclude"},
            {"decision": "include"},
            {"decision": "exclude"},
        ]
        assert count_excluded(log) == 2

    def test_empty(self):
        assert count_excluded([]) == 0

    def test_no_excludes(self):
        log = [{"decision": "include"}, {"decision": "flag_for_full_text"}]
        assert count_excluded(log) == 0

    def test_missing_decision_key(self):
        log = [{"paper_id": "p1"}]
        assert count_excluded(log) == 0


# --- count_flagged ---

class TestCountFlagged:
    def test_basic(self):
        log = [
            {"decision": "flag_for_full_text"},
            {"decision": "include"},
            {"decision": "flag_for_full_text"},
        ]
        assert count_flagged(log) == 2

    def test_empty(self):
        assert count_flagged([]) == 0

    def test_no_flagged(self):
        log = [{"decision": "include"}, {"decision": "exclude"}]
        assert count_flagged(log) == 0


# --- count_included ---

class TestCountIncluded:
    def test_basic(self):
        assert count_included([{"id": "p1"}, {"id": "p2"}]) == 2

    def test_empty(self):
        assert count_included([]) == 0


# --- count_candidates ---

class TestCountCandidates:
    def test_basic(self):
        assert count_candidates([{"id": "c1"}, {"id": "c2"}, {"id": "c3"}]) == 3

    def test_empty(self):
        assert count_candidates([]) == 0


# --- max_snowball_depth ---

class TestMaxSnowballDepth:
    def test_basic(self):
        log = [
            {"depth_level": 1},
            {"depth_level": 3},
            {"depth_level": 2},
        ]
        assert max_snowball_depth(log) == 3

    def test_empty(self):
        assert max_snowball_depth([]) == 0

    def test_missing_depth_level(self):
        log = [{"source_paper_id": "p1"}]
        assert max_snowball_depth(log) == 0

    def test_single_entry(self):
        assert max_snowball_depth([{"depth_level": 5}]) == 5


# --- count_concepts ---

class TestCountConcepts:
    def test_basic(self):
        assert count_concepts([{"concept_id": "c1"}, {"concept_id": "c2"}]) == 2

    def test_empty(self):
        assert count_concepts([]) == 0


# --- count_extractions ---

class TestCountExtractions:
    def test_basic(self):
        extractions = [
            {"paper_id": "p1", "fields": []},
            {"paper_id": "p2", "fields": []},
            {"paper_id": "p3", "fields": []},
        ]
        assert count_extractions(extractions) == 3

    def test_empty(self):
        assert count_extractions([]) == 0

    def test_deduplication(self):
        """Same paper_id appearing multiple times counts as 1."""
        extractions = [
            {"paper_id": "p1", "fields": []},
            {"paper_id": "p1", "fields": []},
            {"paper_id": "p2", "fields": []},
        ]
        assert count_extractions(extractions) == 2

    def test_missing_paper_id_excluded(self):
        """Entries without paper_id are silently skipped."""
        extractions = [
            {"paper_id": "p1"},
            {"fields": []},
        ]
        assert count_extractions(extractions) == 1


# --- recompute_all ---

class TestRecomputeAll:
    def test_representative_inputs(self):
        screening_log = [
            {"decision": "exclude"},
            {"decision": "include"},
            {"decision": "flag_for_full_text"},
            {"decision": "exclude"},
        ]
        candidates = [{"id": "c1"}, {"id": "c2"}, {"id": "c3"}]
        included = [{"id": "p1"}]
        snowball_log = [{"depth_level": 1}, {"depth_level": 2}]
        extractions = [{"paper_id": "p1"}, {"paper_id": "p2"}]
        concepts = [{"concept_id": "x"}, {"concept_id": "y"}, {"concept_id": "z"}]

        result = recompute_all(
            screening_log, candidates, included,
            snowball_log, extractions, concepts,
        )
        assert result["total_candidates"] == 3
        assert result["total_included"] == 1
        assert result["total_excluded"] == 2
        assert result["total_flagged"] == 1
        assert result["snowball_depth_reached"] == 2
        assert result["concepts_count"] == 3
        assert result["extraction_complete_count"] == 2

    def test_all_empty(self):
        result = recompute_all([], [], [], [], [], [])
        assert result["total_candidates"] == 0
        assert result["total_included"] == 0
        assert result["total_excluded"] == 0
        assert result["total_flagged"] == 0
        assert result["snowball_depth_reached"] == 0
        assert result["concepts_count"] == 0
        assert result["extraction_complete_count"] == 0

    def test_accounting_identity(self):
        """excluded + flagged + included_decisions == total screened entries with decisions."""
        screening_log = [
            {"decision": "exclude"},
            {"decision": "include"},
            {"decision": "flag_for_full_text"},
            {"decision": "include"},
            {"decision": "exclude"},
        ]
        excluded = count_excluded(screening_log)
        flagged = count_flagged(screening_log)
        included_decisions = sum(
            1 for e in screening_log if e.get("decision") == "include"
        )
        assert excluded + flagged + included_decisions == len(screening_log)
