"""Tests for section_parser — verified properties + edge cases."""

from lib.section_parser import (
    parse_sections,
    find_sections_by_pattern,
    get_extraction_context,
)


# --- Property: Coverage (P1) ---

def test_empty_text_returns_empty():
    assert parse_sections("") == []


def test_no_headings_returns_single_preamble():
    text = "Just some text without any headings."
    sections = parse_sections(text)
    assert len(sections) == 1
    assert sections[0]["heading"] == "preamble"
    assert sections[0]["start"] == 0
    assert sections[0]["end"] == len(text)


def test_coverage_union_equals_full_text():
    text = "Preamble\n\n# Intro\nSome text\n\n## Methods\nMore text\n\n# Results\nFinal"
    sections = parse_sections(text)
    assert sections[0]["start"] == 0
    assert sections[-1]["end"] == len(text)


# --- Property: Contiguity (P2) ---

def test_contiguity_no_gaps():
    text = "# A\nText A\n\n# B\nText B\n\n# C\nText C"
    sections = parse_sections(text)
    for i in range(len(sections) - 1):
        assert sections[i]["end"] == sections[i + 1]["start"], (
            f"Gap between section {i} and {i+1}"
        )


# --- Property: Ordering (P3) ---

def test_ordering_monotonic():
    text = "Pre\n\n# One\nA\n\n## Two\nB\n\n### Three\nC"
    sections = parse_sections(text)
    for i in range(len(sections)):
        assert sections[i]["start"] < sections[i]["end"]
    for i in range(len(sections) - 1):
        assert sections[i]["start"] < sections[i + 1]["start"]


# --- Property: Heading Level Range (P4) ---

def test_heading_levels_in_range():
    text = "# H1\n## H2\n### H3\n#### H4\n##### H5\n###### H6\n"
    sections = parse_sections(text)
    for s in sections:
        assert 0 <= s["level"] <= 6


def test_preamble_level_zero():
    text = "Preamble text\n\n# Heading\nBody"
    sections = parse_sections(text)
    assert sections[0]["level"] == 0
    assert sections[0]["heading"] == "preamble"


# --- find_sections_by_pattern ---

def test_find_sections_case_insensitive():
    sections = [
        {"heading": "Introduction", "level": 1, "start": 0, "end": 100},
        {"heading": "Methodology", "level": 1, "start": 100, "end": 200},
        {"heading": "Results", "level": 1, "start": 200, "end": 300},
    ]
    matched = find_sections_by_pattern(sections, ["method"])
    assert len(matched) == 1
    assert matched[0]["heading"] == "Methodology"


def test_find_sections_no_match_returns_empty():
    sections = [
        {"heading": "Introduction", "level": 1, "start": 0, "end": 100},
    ]
    assert find_sections_by_pattern(sections, ["nonexistent"]) == []


def test_find_sections_preserves_order():
    sections = [
        {"heading": "Related Work", "level": 2, "start": 0, "end": 50},
        {"heading": "Methods", "level": 1, "start": 50, "end": 100},
        {"heading": "Background", "level": 2, "start": 100, "end": 150},
    ]
    matched = find_sections_by_pattern(sections, ["method", "background"])
    assert [m["heading"] for m in matched] == ["Methods", "Background"]


# --- get_extraction_context ---

def test_extraction_context_routes_to_sections():
    text = "# Introduction\nIntro text\n\n# Methods\nWe used X approach.\n\n# Results\nWe found Y."
    result = get_extraction_context(text, "methodology")
    assert "source" in result
    assert result["source"] == "full_text"
    assert "Methods" in result["sections_used"]


def test_extraction_context_fallback_full_document():
    text = "# Introduction\nSome text\n\n# Conclusion\nEnd"
    result = get_extraction_context(text, "some_unknown_field")
    assert result["source"] == "full_document"


# --- Edge cases ---

def test_whitespace_only_preamble_excluded():
    text = "   \n\n# Heading\nBody text"
    sections = parse_sections(text)
    # Whitespace-only preamble should not be a separate section
    assert sections[0]["heading"] == "Heading"
    assert sections[0]["start"] == 0  # Coverage: starts at 0


def test_heading_with_no_body():
    text = "# A\n# B\n# C\n"
    sections = parse_sections(text)
    assert len(sections) == 3
    for s in sections:
        assert s["start"] < s["end"]
