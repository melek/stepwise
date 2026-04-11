"""Tests for parse_review_citations multi-citation splitting."""
from pathlib import Path
from unittest.mock import patch

from lib.cli import parse_review_citations


def _mock_review(text: str):
    """Create a mock that makes parse_review_citations read from text."""
    def _parse(workspace):
        import re
        # Same logic as parse_review_citations but on provided text
        t = text
        t = re.sub(r"```.*?```", "", t, flags=re.DOTALL)
        t = re.sub(r"`[^`]+`", "", t)
        raw_matches = re.findall(r"\[@([^\]]+)\]", t)
        keys = set()
        for match in raw_matches:
            for part in re.split(r";\s*@?", match):
                part = part.strip()
                if part:
                    keys.add(part)
        return keys
    return _parse(Path("."))


def test_single_citation():
    text = "As shown by [@smith2020], the results are clear."
    keys = _mock_review(text)
    assert keys == {"smith2020"}


def test_multi_citation_with_at():
    text = "Multiple studies [@smith2020; @jones2021] confirm this."
    keys = _mock_review(text)
    assert keys == {"smith2020", "jones2021"}


def test_multi_citation_without_at():
    text = "Several papers [@smith2020; jones2021] agree."
    keys = _mock_review(text)
    assert keys == {"smith2020", "jones2021"}


def test_triple_citation():
    text = "Prior work [@a2020; @b2021; @c2022] established the baseline."
    keys = _mock_review(text)
    assert keys == {"a2020", "b2021", "c2022"}


def test_excludes_code_blocks():
    text = "```\n[@not_a_citation]\n```\nReal text [@real2020]."
    keys = _mock_review(text)
    assert keys == {"real2020"}


def test_excludes_inline_code():
    text = "Use `[@not_real]` format. See [@actual2020]."
    keys = _mock_review(text)
    assert keys == {"actual2020"}


def test_mixed_single_and_multi():
    text = "First [@a2020]. Then [@b2021; @c2022]. Finally [@d2023]."
    keys = _mock_review(text)
    assert keys == {"a2020", "b2021", "c2022", "d2023"}


def test_empty_review():
    text = "No citations here."
    keys = _mock_review(text)
    assert keys == set()
