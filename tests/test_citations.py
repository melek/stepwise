"""Tests for parse_review_citations multi-citation splitting and _split_citation_keys."""
import tempfile
from pathlib import Path

from lib.cli import parse_review_citations
from lib.postconditions import _split_citation_keys, validate_synthesis_claims


def _workspace_with_review(text: str) -> Path:
    """Create a temp directory with review.md containing the given text."""
    d = Path(tempfile.mkdtemp())
    (d / "review.md").write_text(text)
    return d


# --- parse_review_citations (real function, real files) ---


def test_single_citation():
    ws = _workspace_with_review("As shown by [@smith2020], the results are clear.")
    assert parse_review_citations(ws) == {"smith2020"}


def test_multi_citation_with_at():
    ws = _workspace_with_review("Multiple studies [@smith2020; @jones2021] confirm this.")
    assert parse_review_citations(ws) == {"smith2020", "jones2021"}


def test_multi_citation_without_at():
    ws = _workspace_with_review("Several papers [@smith2020; jones2021] agree.")
    assert parse_review_citations(ws) == {"smith2020", "jones2021"}


def test_triple_citation():
    ws = _workspace_with_review("Prior work [@a2020; @b2021; @c2022] established the baseline.")
    assert parse_review_citations(ws) == {"a2020", "b2021", "c2022"}


def test_excludes_code_blocks():
    ws = _workspace_with_review("```\n[@not_a_citation]\n```\nReal text [@real2020].")
    assert parse_review_citations(ws) == {"real2020"}


def test_excludes_inline_code():
    ws = _workspace_with_review("Use `[@not_real]` format. See [@actual2020].")
    assert parse_review_citations(ws) == {"actual2020"}


def test_mixed_single_and_multi():
    ws = _workspace_with_review("First [@a2020]. Then [@b2021; @c2022]. Finally [@d2023].")
    assert parse_review_citations(ws) == {"a2020", "b2021", "c2022", "d2023"}


def test_empty_review():
    ws = _workspace_with_review("No citations here.")
    assert parse_review_citations(ws) == set()


def test_missing_review_file():
    ws = Path(tempfile.mkdtemp())  # no review.md
    assert parse_review_citations(ws) == set()


# --- _split_citation_keys helper ---


def test_split_single_key():
    assert _split_citation_keys("smith2020") == ["smith2020"]


def test_split_multi_with_at():
    assert _split_citation_keys("smith2020; @jones2021") == ["smith2020", "jones2021"]


def test_split_multi_without_at():
    assert _split_citation_keys("smith2020; jones2021") == ["smith2020", "jones2021"]


def test_split_empty():
    assert _split_citation_keys("") == []


# --- validate_synthesis_claims multi-citation (C1 fix) ---


def test_synthesis_claims_multi_citation_resolved():
    """Multi-citation [@key1; @key2] should resolve to individual keys."""
    paragraphs = [{"text": "Both papers [@a2020; @b2021] agree.", "section": "3.1"}]
    included = {"a2020", "b2021"}
    completeness = {"a2020": 1.0, "b2021": 1.0}
    satisfied, failures = validate_synthesis_claims(paragraphs, included, completeness)
    assert satisfied is True


def test_synthesis_claims_multi_citation_absent_key():
    """If one key in a multi-citation is absent, it should be flagged."""
    paragraphs = [{"text": "Both papers [@a2020; @missing] agree.", "section": "3.1"}]
    included = {"a2020"}
    completeness = {"a2020": 1.0}
    satisfied, failures = validate_synthesis_claims(paragraphs, included, completeness)
    assert satisfied is False
    assert any("missing" in f for f in failures)


def test_synthesis_claims_multi_citation_low_completeness():
    """Low-completeness key in multi-citation needs qualification."""
    paragraphs = [{"text": "Results [@good; @weak] show this.", "section": "3.1"}]
    included = {"good", "weak"}
    completeness = {"good": 1.0, "weak": 0.2}
    satisfied, failures = validate_synthesis_claims(paragraphs, included, completeness)
    assert satisfied is False
    assert any("weak" in f and "qualification" in f for f in failures)
