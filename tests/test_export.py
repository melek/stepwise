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
