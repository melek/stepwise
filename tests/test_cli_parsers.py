"""Tests for cli.py protocol parsing functions."""
import json
import pytest
from pathlib import Path

from lib.cli import parse_protocol_queries, _normalize_database


SAMPLE_PROTOCOL = """\
# Research Protocol

## Research Question

**Primary question:** Example question?

### Sub-questions

1. Sub-question one?

## Search Strategy

### Search Terms

| Database | Query String |
|----------|-------------|
| Semantic Scholar | `"formal verification" AND "safety-critical"` |
| Semantic Scholar | `"runtime monitoring" AND "procedures"` |
| arXiv | `"formal methods" AND "operational procedures"` (cs.SE, cs.FL) |

### Databases

- Semantic Scholar
- arXiv

### Date Range

- **Start year:** 2010
- **End year:** 2026

## Selection Criteria

### Inclusion Criteria

| ID | Description | Testable Condition |
|----|-------------|--------------------|
| IC1 | Addresses verification | Paper describes a method |
| IC2 | Structured procedures | Has preconditions |

### Exclusion Criteria

| ID | Description | Testable Condition |
|----|-------------|--------------------|
| EC1 | Pure software verification | No procedural component |

## Quality Assessment Checklist

| ID | Question |
|----|----------|
| QA1 | Is the formalism defined? |

## Data Extraction Schema

| Field Name | Type | Description |
|------------|------|-------------|
| paper_id | string | Canonical ID |
| title | string | Paper title |

## Phase Bounds

| Parameter | Value |
|-----------|-------|
| max_results_per_query | 50 |
| max_snowball_depth | 1 |
"""


@pytest.fixture
def protocol_workspace(tmp_path):
    (tmp_path / "protocol.md").write_text(SAMPLE_PROTOCOL)
    return tmp_path


def test_parse_protocol_queries_scoped(protocol_workspace):
    """Parser returns only Search Terms rows, not criteria/QA/schema/bounds."""
    queries = parse_protocol_queries(protocol_workspace)
    assert len(queries) == 3


def test_parse_protocol_queries_normalizes_db(protocol_workspace):
    queries = parse_protocol_queries(protocol_workspace)
    dbs = [q["database"] for q in queries]
    assert dbs == ["semantic_scholar", "semantic_scholar", "arxiv"]


def test_parse_protocol_queries_strips_backticks(protocol_workspace):
    queries = parse_protocol_queries(protocol_workspace)
    for q in queries:
        assert "`" not in q["query"]


def test_parse_protocol_queries_strips_category_annotations(protocol_workspace):
    queries = parse_protocol_queries(protocol_workspace)
    arxiv_q = [q for q in queries if q["database"] == "arxiv"][0]
    assert "(cs.SE" not in arxiv_q["query"]
    assert arxiv_q["query"] == '"formal methods" AND "operational procedures"'


def test_parse_protocol_queries_missing_section(tmp_path):
    (tmp_path / "protocol.md").write_text("# Protocol\n\nNo search terms here.\n")
    assert parse_protocol_queries(tmp_path) == []


def test_parse_protocol_queries_missing_file(tmp_path):
    assert parse_protocol_queries(tmp_path) == []


def test_normalize_database():
    assert _normalize_database("Semantic Scholar") == "semantic_scholar"
    assert _normalize_database("arXiv") == "arxiv"
    assert _normalize_database("PubMed") == "pubmed"
    assert _normalize_database("semantic_scholar") == "semantic_scholar"
    assert _normalize_database("Some New DB") == "some_new_db"
