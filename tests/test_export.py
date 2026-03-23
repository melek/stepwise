"""Tests for export functions."""

from lib.export import generate_prisma_flow_diagram


def test_generates_mermaid_syntax():
    metrics = {"search_candidates": 150, "snowball_candidates": 45, "deduplicated": 180,
               "screened": 180, "excluded": 140, "flagged": 12, "ft_excluded": 8, "included": 32}
    diagram = generate_prisma_flow_diagram(metrics)
    assert "graph TD" in diagram
    assert "150" in diagram
    assert "32" in diagram


def test_contains_prisma_flow_nodes():
    metrics = {"search_candidates": 100, "snowball_candidates": 20, "deduplicated": 110,
               "screened": 110, "excluded": 80, "flagged": 5, "ft_excluded": 3, "included": 27}
    diagram = generate_prisma_flow_diagram(metrics)
    lower = diagram.lower()
    assert "search" in lower
    assert "snowball" in lower
    assert "screened" in lower
    assert "included" in lower
    assert "excluded" in lower


from lib.export import to_ris, to_csv


def test_ris_basic_format():
    records = [
        {"id": "10.1234/test", "title": "Test Paper", "authors": ["Alice", "Bob"],
         "year": 2024, "venue": "ICSE", "doi": "10.1234/test", "abstract": "A test."},
    ]
    ris = to_ris(records)
    assert "TY  - JOUR" in ris
    assert "TI  - Test Paper" in ris
    assert "AU  - Alice" in ris
    assert "AU  - Bob" in ris
    assert "PY  - 2024" in ris
    assert "DO  - 10.1234/test" in ris
    assert "ER  -" in ris


def test_ris_multiple_records():
    records = [
        {"id": "1", "title": "Paper 1", "authors": ["A"], "year": 2024},
        {"id": "2", "title": "Paper 2", "authors": ["B"], "year": 2025},
    ]
    ris = to_ris(records)
    assert ris.count("ER  -") == 2


def test_csv_basic_format():
    records = [
        {"id": "1", "title": "Test Paper", "authors": ["Alice", "Bob"], "year": 2024,
         "venue": "ICSE", "doi": "10.1234/test"},
    ]
    csv_out = to_csv(records, ["id", "title", "year", "venue"])
    lines = csv_out.strip().split("\n")
    assert lines[0] == "id,title,year,venue"
    assert "Test Paper" in lines[1]
    assert "2024" in lines[1]


def test_csv_handles_commas_in_values():
    records = [
        {"id": "1", "title": "Papers, Reviews, and More", "authors": ["A"], "year": 2024},
    ]
    csv_out = to_csv(records, ["id", "title"])
    assert '"Papers, Reviews, and More"' in csv_out


def test_ris_empty_records():
    assert to_ris([]) == ""


def test_csv_empty_records():
    csv_out = to_csv([], ["id", "title"])
    assert csv_out.strip() == "id,title"
