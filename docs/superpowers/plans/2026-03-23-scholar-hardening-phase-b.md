# Scholar Hardening Phase B — Capability Expansion

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Expand Scholar's data sources (PubMed, Scite, paper-search-mcp), add citation hallucination detection, and enable RIS/CSV export for interoperability.

**Architecture:** Runbook and skill modifications to integrate new MCP servers as optional data sources. New pure functions in `lib/postconditions.py` (hallucination detection) and `lib/export.py` (RIS/CSV). All new MCP integrations degrade gracefully — Scholar works without them, just with reduced coverage.

**Tech Stack:** Python 3.10+, pytest, existing MCP servers

**Spec:** `docs/superpowers/specs/2026-03-22-scholar-hardening-design.md` (v1.1), Section 6

---

## File Map

### Modified Files

| File | Changes |
|------|---------|
| `runbooks/search.md` | Add PubMed and paper-search-mcp query execution blocks, rate limits |
| `runbooks/screen.md` | Add optional Scite citation context lookup |
| `runbooks/extract.md` | Add optional Scite citation classification enrichment |
| `skills/research/SKILL.md` | Add PubMed, Scite, paper-search-mcp to allowed-tools |
| `skills/continue/SKILL.md` | Same allowed-tools update |
| `templates/protocol-template.md` | Add PubMed row to Search Terms table |
| `lib/postconditions.py` | Add `check_citation_grounding` function |
| `lib/export.py` | Add `to_ris` and `to_csv` functions |
| `lib/cli.py` | Add `export` subcommand |
| `tests/test_oracle_contracts.py` | Add citation grounding tests |
| `tests/test_export.py` | Add RIS/CSV tests |

---

## Task 1: PubMed MCP Integration in Search Runbook

**Files:**
- Modify: `runbooks/search.md`
- Modify: `templates/protocol-template.md`
- Modify: `skills/research/SKILL.md`
- Modify: `skills/continue/SKILL.md`

- [ ] **Step 1: Read current `runbooks/search.md` Step 2**

Note how Semantic Scholar and arXiv queries are structured. PubMed follows the same pattern.

- [ ] **Step 2: Add PubMed query block to `runbooks/search.md` Step 2**

After the arXiv block, add:

```markdown
**PubMed (if available):**
- Check if `mcp__pubmed__search` is in the tool list. If not, skip and log:
  ```json
  {"timestamp": "{ISO-8601}", "event": "pubmed_unavailable", "phase": 1, "details": {"reason": "MCP not configured"}}
  ```
- Use `mcp__pubmed__search` with the query string
- Parameters: query={query}, max_results={max_results_per_query}
- Record each result's: PMID, title, abstract, authors, year, journal, DOI
- Map PMID to canonical ID: use DOI if available, else PMID as `pmid:{PMID}`
```

- [ ] **Step 3: Add PubMed to rate limit table**

Add row to the Rate Limit Handling table:

```markdown
| PubMed | 0.33 seconds (3 RPS) |
```

- [ ] **Step 4: Add PubMed row to `templates/protocol-template.md` Search Terms table**

```markdown
| PubMed | [TODO] |
```

- [ ] **Step 5: Add PubMed MCP tools to `skills/research/SKILL.md` allowed-tools**

Add to the comma-separated allowed-tools list: `mcp__pubmed__search, mcp__pubmed__get_article, mcp__pubmed__get_related`

- [ ] **Step 6: Same update to `skills/continue/SKILL.md` allowed-tools**

- [ ] **Step 7: Commit**

```bash
git add runbooks/search.md templates/protocol-template.md skills/research/SKILL.md skills/continue/SKILL.md
git commit -m "feat: add PubMed MCP integration to search pipeline"
```

---

## Task 2: Scite MCP Integration in Screening and Extraction

**Files:**
- Modify: `runbooks/screen.md`
- Modify: `runbooks/extract.md`
- Modify: `skills/research/SKILL.md`
- Modify: `skills/continue/SKILL.md`

- [ ] **Step 1: Read `runbooks/screen.md` Step 3A**

Understand the current criterion evaluation flow.

- [ ] **Step 2: Add optional Scite lookup to `runbooks/screen.md`**

Add after Step 3A (before Step 3B exclusion criteria), as Step 3A-bis:

```markdown
**A-bis. Enrich with Scite citation context (optional):**
If `mcp__scite__search_citations` is in the tool list:
1. Query Scite for the paper's DOI (if available)
2. Record: total citations, supporting count, contrasting count, mentioning count
3. If contrasting citations > 30% of total: note this as additional evidence for criterion evaluations
4. Append Scite context to the evidence field: `"Scite: {supporting} supporting, {contrasting} contrasting, {mentioning} mentioning"`

If Scite MCP is unavailable, skip silently. This step is purely additive — it enriches evidence but never overrides criterion judgments.
```

- [ ] **Step 3: Add Scite enrichment to `runbooks/extract.md`**

Add after Step 4C (concept identification), as Step 4C-bis:

```markdown
**C-bis. Scite citation classification (optional):**
If `mcp__scite__search_citations` is in the tool list and the paper has a DOI:
1. Query Scite for citation statements about this paper
2. For each citing paper that is also in `included.jsonl`:
   - Record the citation classification (supporting/contrasting/mentioning)
   - Add to extraction record: `"scite_context": [{"citing_paper": "id", "classification": "supporting"}]`
3. This enriches the concept matrix with agreement/disagreement relationships

If Scite MCP is unavailable, skip. Extraction proceeds normally without Scite data.
```

- [ ] **Step 4: Add Scite tools to allowed-tools in both skill files**

Add: `mcp__scite__search_citations, mcp__scite__get_paper_citations`

- [ ] **Step 5: Add Scite to search runbook rate limit table**

```markdown
| Scite | 1 second |
```

- [ ] **Step 6: Commit**

```bash
git add runbooks/screen.md runbooks/extract.md skills/research/SKILL.md skills/continue/SKILL.md runbooks/search.md
git commit -m "feat: add optional Scite MCP for citation context in screening and extraction"
```

---

## Task 3: paper-search-mcp Integration

**Files:**
- Modify: `runbooks/search.md`
- Modify: `skills/research/SKILL.md`
- Modify: `skills/continue/SKILL.md`

- [ ] **Step 1: Add paper-search-mcp block to `runbooks/search.md` Step 2**

After the PubMed block:

```markdown
**paper-search-mcp (if available):**
- Check if `mcp__paper_search__search_papers` is in the tool list. If not, skip and log:
  ```json
  {"timestamp": "{ISO-8601}", "event": "paper_search_unavailable", "phase": 1, "details": {"reason": "MCP not configured"}}
  ```
- Use `mcp__paper_search__search_papers` with the query string
- This searches 20+ databases simultaneously (IEEE Xplore, ACM, DBLP, CrossRef, OpenAlex, CORE, etc.)
- Deduplicate results against existing candidates using DOI matching
- Record source as "paper-search-mcp" in `discovered_by_query`
```

- [ ] **Step 2: Add paper-search-mcp to allowed-tools in both skill files**

Add: `mcp__paper_search__search_papers, mcp__paper_search__download_with_fallback`

- [ ] **Step 3: Commit**

```bash
git add runbooks/search.md skills/research/SKILL.md skills/continue/SKILL.md
git commit -m "feat: add paper-search-mcp integration for broad database coverage"
```

---

## Task 4: Citation Hallucination Detection

**Files:**
- Modify: `lib/postconditions.py`
- Modify: `tests/test_oracle_contracts.py`

- [ ] **Step 1: Write failing tests**

Add to `tests/test_oracle_contracts.py`:

```python
from lib.postconditions import check_citation_grounding


def test_grounded_citation_passes():
    review_citations = {
        "dijkstra1968": "Formal verification improves software reliability",
    }
    extractions = [
        {"paper_id": "dijkstra1968", "fields": [
            {"field_name": "key_finding", "value": "formal verification improves reliability"},
        ]},
    ]
    ok, failures = check_citation_grounding(review_citations, extractions)
    assert ok is True


def test_ungrounded_citation_flagged():
    review_citations = {
        "dijkstra1968": "Machine learning models achieve 99% accuracy",
    }
    extractions = [
        {"paper_id": "dijkstra1968", "fields": [
            {"field_name": "key_finding", "value": "formal verification improves reliability"},
        ]},
    ]
    ok, failures = check_citation_grounding(review_citations, extractions)
    assert ok is False
    assert any("dijkstra1968" in f for f in failures)


def test_missing_extraction_flagged():
    review_citations = {
        "ghost2099": "This paper shows great results",
    }
    extractions = []
    ok, failures = check_citation_grounding(review_citations, extractions)
    assert ok is False
    assert any("ghost2099" in f for f in failures)


def test_empty_citations_passes():
    ok, failures = check_citation_grounding({}, [])
    assert ok is True
```

- [ ] **Step 2: Run tests, verify they fail**

Run: `.venv/bin/python3 -m pytest tests/test_oracle_contracts.py -v -k "grounding"`
Expected: FAIL — ImportError

- [ ] **Step 3: Implement `check_citation_grounding`**

Add to `lib/postconditions.py`:

```python
def check_citation_grounding(
    review_citations: dict[str, str],
    extractions: list[dict],
    min_overlap: int = 2,
) -> tuple[bool, list[str]]:
    """Check that cited papers' extraction data supports the claim sentence.

    Advisory check: flags potentially ungrounded citations.
    review_citations: {bibtex_key: surrounding_sentence}
    extractions: list of extraction records with paper_id and fields
    min_overlap: minimum keyword overlap count to consider grounded
    """
    failures = []
    extraction_map = {e["paper_id"]: e for e in extractions if "paper_id" in e}

    for key, claim_sentence in review_citations.items():
        if key not in extraction_map:
            failures.append(f"[@{key}]: no extraction record found — cannot verify grounding")
            continue

        ext = extraction_map[key]
        # Collect all extracted values into one text block
        extracted_text = " ".join(
            f.get("value", "") for f in ext.get("fields", [])
            if f.get("value") and f.get("value") != "extraction_failed"
        ).lower()

        if not extracted_text:
            failures.append(f"[@{key}]: all extraction fields failed — cannot verify grounding")
            continue

        # Simple keyword overlap check
        claim_words = set(re.findall(r"[a-z]{3,}", claim_sentence.lower()))
        extract_words = set(re.findall(r"[a-z]{3,}", extracted_text))
        overlap = claim_words & extract_words

        if len(overlap) < min_overlap:
            failures.append(
                f"[@{key}]: low keyword overlap ({len(overlap)} words) between claim and extraction — "
                f"potentially ungrounded citation"
            )

    return _result(failures)
```

- [ ] **Step 4: Run tests**

Run: `.venv/bin/python3 -m pytest tests/ -v`
Expected: 79 passed (75 + 4 new)

- [ ] **Step 5: Commit**

```bash
git add lib/postconditions.py tests/test_oracle_contracts.py
git commit -m "feat: add citation hallucination detection (advisory postcondition)"
```

---

## Task 5: RIS and CSV Export

**Files:**
- Modify: `lib/export.py`
- Modify: `lib/cli.py`
- Modify: `tests/test_export.py`

- [ ] **Step 1: Write failing tests**

Add to `tests/test_export.py`:

```python
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
```

- [ ] **Step 2: Run tests, verify they fail**

Run: `.venv/bin/python3 -m pytest tests/test_export.py -v -k "ris or csv"`
Expected: FAIL — ImportError

- [ ] **Step 3: Add `to_ris` and `to_csv` to `lib/export.py`**

```python
import csv
import io


def to_ris(records: list[dict]) -> str:
    """Convert paper records to RIS format.

    Produces RIS entries importable by Zotero, Mendeley, Covidence, Rayyan.
    """
    if not records:
        return ""

    lines = []
    for rec in records:
        lines.append("TY  - JOUR")
        if rec.get("title"):
            lines.append(f"TI  - {rec['title']}")
        for author in rec.get("authors", []):
            lines.append(f"AU  - {author}")
        if rec.get("year"):
            lines.append(f"PY  - {rec['year']}")
        if rec.get("venue"):
            lines.append(f"JO  - {rec['venue']}")
        if rec.get("doi"):
            lines.append(f"DO  - {rec['doi']}")
        if rec.get("abstract"):
            lines.append(f"AB  - {rec['abstract']}")
        if rec.get("id"):
            lines.append(f"ID  - {rec['id']}")
        lines.append("ER  -")
        lines.append("")

    return "\n".join(lines)


def to_csv(records: list[dict], fields: list[str]) -> str:
    """Convert paper records to CSV format.

    fields: list of field names to include as columns.
    Values containing commas are quoted per RFC 4180.
    """
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=fields, extrasaction="ignore")
    writer.writeheader()
    for rec in records:
        # Flatten list values (e.g., authors) to semicolon-separated
        row = {}
        for f in fields:
            val = rec.get(f, "")
            if isinstance(val, list):
                val = "; ".join(str(v) for v in val)
            row[f] = val
        writer.writerow(row)
    return output.getvalue()
```

- [ ] **Step 4: Add `export` CLI subcommand to `lib/cli.py`**

Read `lib/cli.py` first. Add handler:

```python
from . import export as exp

def cmd_export(args: argparse.Namespace) -> None:
    workspace = Path(args.workspace).expanduser()
    data = load_workspace_data(workspace)

    dataset_map = {
        "candidates": data["candidates"],
        "included": data["included"],
        "extractions": data["extractions"],
    }
    records = dataset_map.get(args.dataset, [])

    if args.format == "ris":
        output = exp.to_ris(records)
    elif args.format == "csv":
        # Default fields for each dataset
        default_fields = {
            "candidates": ["id", "title", "authors", "year", "venue", "doi", "source"],
            "included": ["id", "title", "authors", "year", "venue", "doi", "source"],
            "extractions": ["paper_id", "source", "timestamp"],
        }
        fields = default_fields.get(args.dataset, ["id", "title"])
        output = exp.to_csv(records, fields)

    output_path = workspace / f"exports/{args.dataset}.{args.format}"
    output_path.parent.mkdir(exist_ok=True)
    output_path.write_text(output)
    json.dump({"written": str(output_path), "records": len(records), "format": args.format},
              sys.stdout, indent=2)
    print()
```

Add argparse:
```python
    # export
    p_exp = sub.add_parser("export", help="Export data to RIS or CSV format")
    p_exp.add_argument("--format", required=True, choices=["ris", "csv"])
    p_exp.add_argument("--dataset", required=True, choices=["candidates", "included", "extractions"])
    p_exp.add_argument("--workspace", required=True)
```

Add to handlers: `"export": cmd_export,`

- [ ] **Step 5: Run ALL tests**

Run: `.venv/bin/python3 -m pytest tests/ -v`
Expected: 85 passed (79 + 6 new)

- [ ] **Step 6: Commit**

```bash
git add lib/export.py lib/cli.py tests/test_export.py
git commit -m "feat: add RIS/CSV export with CLI subcommand"
```

---

## Task 6: Final Integration Verification

- [ ] **Step 1: Run full test suite**

```bash
.venv/bin/python3 -m pytest tests/ -v
```

- [ ] **Step 2: Verify all CLI subcommands**

```bash
# Phase A commands
.venv/bin/python3 -m lib.cli validate-inference --contract SCREEN_CRITERION --record '{"criterion_id":"IC1","criterion_type":"inclusion","met":"yes","evidence":"test","source":"abstract"}'

# Phase B commands
.venv/bin/python3 -m lib.cli export --format ris --dataset included --workspace /tmp/nonexistent 2>&1 || true
```

- [ ] **Step 3: Verify runbook changes are syntactically valid markdown**

```bash
# Quick check: all runbooks parse without errors
for f in runbooks/*.md; do echo "--- $f ---"; head -3 "$f"; done
```

- [ ] **Step 4: Final commit if cleanup needed**
