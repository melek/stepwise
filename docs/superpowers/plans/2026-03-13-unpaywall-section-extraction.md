# Unpaywall Integration + Section-Guided Extraction

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add Unpaywall as a full-text source for DOI-bearing papers, and implement section-guided extraction so the extract agent works with focused context windows instead of full documents.

**Architecture:** Three layers of change: (1) a new verified `section_parser.py` module that deterministically splits markdown text into sections, exposed via `cli.py parse-sections`; (2) search runbook gains an Unpaywall download step for DOI-bearing papers without arXiv full text; (3) extract runbook gains a section-guided procedure that parses full-text papers into sections and routes schema fields to relevant sections before extraction. Papers without full text remain abstract-only (existing behavior). The design spec and dependency table are updated to reflect the new data source and two-tier extraction model.

**Tech Stack:** Python 3.10+ (fractions.Fraction for verified code), Dafny/Proven for formal verification, Unpaywall MCP (`npx -y unpaywall-mcp`), existing arXiv + Semantic Scholar MCPs.

---

## File Map

| File | Action | Responsibility |
|------|--------|---------------|
| `scholar/lib/section_parser.py` | Create | Pure functions: `parse_sections(text) → list[Section]`, verified properties |
| `scholar/lib/cli.py` | Modify | Add `parse-sections` command that calls section_parser |
| `scholar/tests/test_section_parser.py` | Create | Property-based + example tests for section parser |
| `scholar/lib/verified/section_parser.dfy` | Create | Dafny proof certificate (produced by Proven) |
| `proven/examples/scholar_section_parser.md` | Create | Proven requirements file for section parser |
| `scholar/runbooks/search.md` | Modify | Add Step 6b: Unpaywall download for DOI papers (after metadata enrichment) |
| `scholar/runbooks/extract.md` | Modify | Add section-guided extraction procedure |
| `scholar/docs/2026-03-12-scholar-design.md` | Modify | Add Unpaywall dependency, two-tier extraction model |
| `scholar/skills/research/SKILL.md` | Modify | Add Unpaywall tools to allowed-tools |
| `scholar/skills/continue/SKILL.md` | Modify | Add Unpaywall tools to allowed-tools |

---

## Chunk 1: Verified Section Parser

### Task 1: Write Proven Requirements

**Files:**
- Create: `proven/examples/scholar_section_parser.md`

The section parser takes markdown text and returns a list of sections. Each section has a heading, level, and character range. Properties to prove: coverage (every character belongs to exactly one section), contiguity (no gaps or overlaps), ordering (boundaries monotonically increase), and heading fidelity (section labels match source headings).

- [ ] **Step 1: Write the requirements file**

```markdown
# Section Parser

## Data Structure

A **Section** has fields:
- `heading`: string (the heading text, or "preamble" for text before the first heading)
- `level`: integer in [0, 6] (0 = preamble, 1-6 = heading levels)
- `start`: non-negative integer (character offset, inclusive)
- `end`: non-negative integer (character offset, exclusive)

Input: `text`, a string of markdown content.
Output: a sequence of Section records (SectionList).

## Operations

1. **ParseSections(text: string) → SectionList**: Split `text` into sections at markdown heading boundaries. A markdown heading is a line that starts with one or more `#` characters followed by a space. The heading level is the count of `#` characters. Rules: (a) If `text` is empty, return an empty sequence. (b) If `text` has no headings, return a single Section with heading="preamble", level=0, start=0, end=|text|. (c) If text before the first heading is non-empty (after stripping whitespace), it becomes a preamble section. (d) Each heading starts a new section. The section's `start` is the character offset of the `#` character. The section's `end` is the `start` of the next section, or `|text|` for the last section. (e) The heading text is extracted by stripping the `#` prefix and leading/trailing whitespace.

2. **FindSectionsByPattern(sections: SectionList, patterns: sequence of strings) → SectionList**: Return sections whose heading matches any pattern (case-insensitive substring match). If no sections match, return an empty list.

## Properties to Prove

- **Coverage**: For non-empty text: the union of all [start, end) intervals equals [0, |text|). Formally: if |text| > 0 then sections[0].start == 0 AND sections[last].end == |text|.
- **Contiguity**: For adjacent sections i, i+1: sections[i].end == sections[i+1].start. No gaps, no overlaps.
- **Ordering**: For all i: sections[i].start < sections[i].end (non-empty sections). For all i < j: sections[i].start < sections[j].start (monotonic).
- **Heading level range**: For all sections: 0 <= level <= 6. Level 0 only for the preamble section (first section, if present and heading == "preamble").
- **Determinism**: Same input text → same output SectionList (pure function, no side effects).
- **FindSections subset**: FindSectionsByPattern returns a subsequence of the input SectionList (preserves order, no new elements).
```

Save to `proven/examples/scholar_section_parser.md`.

- [ ] **Step 2: Commit requirements**

```bash
git -C /home/melek/workshop/proven add examples/scholar_section_parser.md
git -C /home/melek/workshop/proven commit -m "feat: add section parser requirements for Scholar"
```

### Task 2: Run Proven Pipeline

**Files:**
- Create: `scholar/lib/verified/section_parser.dfy` (from Proven output)
- Create: `scholar/lib/section_parser.py` (from Proven output or hand-written to match spec)

- [ ] **Step 1: Run Proven**

```bash
cd /home/melek/workshop/proven
python -m proven run examples/scholar_section_parser.md --mode autonomous
```

If Proven succeeds: copy the generated `.dfy` file to `scholar/lib/verified/section_parser.dfy` and the Python output to `scholar/lib/section_parser.py`.

If Proven fails (spec drift or preprocessor issues, as seen with postcond_p3-p5): hand-write both the Dafny spec and the Python implementation matching the requirements. Verify the Dafny directly with `dafny verify`.

- [ ] **Step 2: Verify Dafny proof passes**

```bash
/home/melek/dafny/dafny/dafny verify /home/melek/workshop/scholar/lib/verified/section_parser.dfy
```

Expected: `N verified, 0 errors`.

- [ ] **Step 3: Write Python implementation (if not produced by Proven)**

Create `scholar/lib/section_parser.py` with these functions:

```python
"""Scholar section parser.

Pure functions for splitting markdown text into sections at heading
boundaries. No file I/O.

Verified properties:
- Coverage: every character belongs to exactly one section
- Contiguity: adjacent sections share boundaries (no gaps/overlaps)
- Ordering: section boundaries are monotonically increasing
- Heading level range: 0-6, 0 only for preamble
"""

import re


def parse_sections(text: str) -> list[dict]:
    """Parse markdown text into sections at heading boundaries.

    Returns list of dicts with keys: heading, level, start, end.
    Each section's text is text[start:end].
    """
    if not text:
        return []

    # Find all heading positions
    heading_pattern = re.compile(r'^(#{1,6})\s+(.+)$', re.MULTILINE)
    headings = list(heading_pattern.finditer(text))

    if not headings:
        return [{"heading": "preamble", "level": 0, "start": 0, "end": len(text)}]

    sections = []

    # Preamble: text before first heading (if non-whitespace content exists)
    first_start = headings[0].start()
    if first_start > 0 and text[:first_start].strip():
        sections.append({
            "heading": "preamble",
            "level": 0,
            "start": 0,
            "end": first_start,
        })

    # Each heading starts a section
    for i, match in enumerate(headings):
        level = len(match.group(1))
        heading_text = match.group(2).strip()
        start = match.start()
        end = headings[i + 1].start() if i + 1 < len(headings) else len(text)
        sections.append({
            "heading": heading_text,
            "level": level,
            "start": start,
            "end": end,
        })

    # If no preamble, ensure coverage starts at 0
    if sections and sections[0]["start"] > 0 and not text[:sections[0]["start"]].strip():
        sections[0] = {**sections[0], "start": 0}

    return sections


def find_sections_by_pattern(
    sections: list[dict], patterns: list[str]
) -> list[dict]:
    """Return sections whose heading matches any pattern (case-insensitive substring).

    Returns a subsequence of the input list (preserves order).
    """
    patterns_lower = [p.lower() for p in patterns]
    return [
        s for s in sections
        if any(p in s["heading"].lower() for p in patterns_lower)
    ]


# Field-to-section mapping: common extraction field names → likely heading patterns
FIELD_SECTION_MAP: dict[str, list[str]] = {
    "methodology": ["method", "approach", "design", "experimental", "procedure"],
    "results": ["result", "finding", "evaluation", "experiment"],
    "limitations": ["limitation", "threat", "weakness"],
    "contributions": ["contribution", "introduction", "abstract"],
    "future_work": ["future", "conclusion", "discussion"],
    "related_work": ["related", "background", "literature", "prior"],
    "dataset": ["data", "dataset", "corpus", "benchmark"],
    "metrics": ["metric", "measure", "evaluation"],
    "architecture": ["architecture", "system", "framework", "model", "design"],
    "theory": ["theory", "formal", "proof", "definition"],
}


def get_extraction_context(
    text: str, field_name: str, max_chars: int = 8000
) -> dict:
    """Get focused context for extracting a specific field.

    Returns {"sections_used": [heading, ...], "context": "text...", "source": "full_text"|"full_document"}.
    If field maps to known sections and those sections exist, returns only those sections' text.
    Otherwise returns the full text (truncated to max_chars).
    """
    sections = parse_sections(text)

    # Normalize field name for lookup
    field_key = field_name.lower().replace(" ", "_").replace("-", "_")
    patterns = FIELD_SECTION_MAP.get(field_key, [])

    if patterns:
        matched = find_sections_by_pattern(sections, patterns)
        if matched:
            context_parts = []
            headings_used = []
            total = 0
            for s in matched:
                section_text = text[s["start"]:s["end"]]
                if total + len(section_text) > max_chars:
                    remaining = max_chars - total
                    if remaining > 200:  # worth including partial
                        context_parts.append(section_text[:remaining])
                        headings_used.append(s["heading"])
                    break
                context_parts.append(section_text)
                headings_used.append(s["heading"])
                total += len(section_text)
            return {
                "sections_used": headings_used,
                "context": "".join(context_parts),
                "source": "full_text",
            }

    # Fallback: return full text (truncated)
    return {
        "sections_used": [s["heading"] for s in sections],
        "context": text[:max_chars],
        "source": "full_document",
    }
```

- [ ] **Step 4: Commit section parser**

```bash
git -C /home/melek/workshop/scholar add lib/section_parser.py lib/verified/section_parser.dfy
git -C /home/melek/workshop/scholar commit -m "feat: add verified section parser for extraction context"
```

### Task 3: Tests for Section Parser

**Files:**
- Create: `scholar/tests/__init__.py`
- Create: `scholar/tests/test_section_parser.py`

- [ ] **Step 1: Write tests**

```python
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
```

- [ ] **Step 2: Run tests**

```bash
cd /home/melek/workshop/scholar && python3 -m pytest tests/test_section_parser.py -v
```

Expected: all pass.

- [ ] **Step 3: Fix any failures, re-run until green**

- [ ] **Step 4: Commit tests**

```bash
git -C /home/melek/workshop/scholar add tests/
git -C /home/melek/workshop/scholar commit -m "test: add section parser tests (coverage, contiguity, ordering)"
```

### Task 4: Integrate Section Parser into CLI

**Files:**
- Modify: `scholar/lib/cli.py`

- [ ] **Step 1: Add parse-sections command to cli.py**

Add import at top:
```python
from . import section_parser as sp
```

Add command handler:
```python
def cmd_parse_sections(args: argparse.Namespace) -> None:
    file_path = Path(args.file).expanduser()
    text = file_path.read_text()

    if args.field:
        result = sp.get_extraction_context(text, args.field, max_chars=args.max_chars)
        json.dump(result, sys.stdout, indent=2)
    else:
        sections = sp.parse_sections(text)
        output = [
            {
                "heading": s["heading"],
                "level": s["level"],
                "start": s["start"],
                "end": s["end"],
                "char_count": s["end"] - s["start"],
            }
            for s in sections
        ]
        json.dump(output, sys.stdout, indent=2)
    print()
```

Add subparser in `main()`:
```python
p_sections = sub.add_parser("parse-sections", help="Parse markdown text into sections")
p_sections.add_argument("--file", required=True, help="Path to text file")
p_sections.add_argument("--field", help="Optional: get extraction context for a specific field")
p_sections.add_argument("--max-chars", type=int, default=8000, help="Max context chars (default 8000)")
```

Add to handlers dict:
```python
"parse-sections": cmd_parse_sections,
```

- [ ] **Step 2: Test CLI manually**

```bash
# Create a small test file
echo -e "# Introduction\nSome intro.\n\n## Methods\nWe did X.\n\n# Results\nY happened." > /tmp/test_paper.txt
cd /home/melek/workshop/scholar && python3 -m lib.cli parse-sections --file /tmp/test_paper.txt
cd /home/melek/workshop/scholar && python3 -m lib.cli parse-sections --file /tmp/test_paper.txt --field methodology
```

Expected: JSON output with sections / focused extraction context.

- [ ] **Step 3: Commit**

```bash
git -C /home/melek/workshop/scholar add lib/cli.py
git -C /home/melek/workshop/scholar commit -m "feat: add parse-sections command to CLI"
```

---

## Chunk 2: Unpaywall Integration + Runbook Updates

### Task 5: Update Design Spec

**Files:**
- Modify: `scholar/docs/2026-03-12-scholar-design.md`

Three changes:

- [ ] **Step 1: Add Unpaywall to dependencies table (§9)**

Add row after arXiv MCP:
```
| Unpaywall MCP | Full-text retrieval for DOI papers | No | Abstract-only extraction for non-arXiv papers |
```

- [ ] **Step 2: Update Phase 1 spec (§2.2, Phase 1)**

In the Process section, after item 2 (Download available PDFs via arXiv MCP), add:

```
3. For candidates with a DOI but no arXiv full text: query Unpaywall for open-access full text. If available, download and write to `papers/` directory. This extends full-text coverage beyond arXiv to any open-access paper with a DOI.
```

Renumber subsequent items.

- [ ] **Step 3: Update Phase 4 spec (§2.2, Phase 4)**

Replace Process item 1:
```
1. Read full text (PDF if available, else abstract + metadata)
```

With:
```
1. Read paper content. If full text available in `papers/`:
   a. Parse text into sections using the verified section parser
   b. For each extraction field, retrieve focused context from the relevant sections
   c. Extract from focused context (not the full document)
   If no full text available: use abstract + metadata from included.jsonl (existing behavior).
   Record which source was used: "full_text" or "abstract".
```

- [ ] **Step 4: Update A6 sovereignty note**

In A6, after "Cloud APIs (Semantic Scholar, arXiv) are used for discovery only." add:
```
Unpaywall is queried with DOIs to locate open-access full text; only the DOI is transmitted.
```

- [ ] **Step 5: Update P7 sovereignty**

In P7, update the exception list:
```
(a) search queries sent to Semantic Scholar/arXiv APIs, (b) DOIs sent to Unpaywall for open-access lookup, (c) paper metadata sent to Zotero for collection management.
```

- [ ] **Step 6: Commit**

```bash
git -C /home/melek/workshop/scholar add docs/2026-03-12-scholar-design.md
git -C /home/melek/workshop/scholar commit -m "spec: add Unpaywall dependency, two-tier extraction model"
```

### Task 6: Update Search Runbook

**Files:**
- Modify: `scholar/runbooks/search.md`

- [ ] **Step 1: Add `source` field to existing arXiv download-log schema**

Update the existing Step 5 download-log.jsonl schema to include a `source` field for consistency:
```json
{"paper_id": "{id}", "arxiv_id": "{arxiv_id}", "source": "arxiv", "timestamp": "{ISO-8601}", "status": "success|error", "error_message": null}
```

- [ ] **Step 2: Add Step 6b after Step 6 (Enrich Metadata)**

Insert after Step 6 (Enrich Metadata), not after Step 5. This ordering is critical: Step 6 enriches arXiv-only candidates with Semantic Scholar metadata, which may discover DOIs that weren't previously known. Running Unpaywall after enrichment catches those newly-discovered DOIs.

```markdown
### Step 6b: Download Papers (Unpaywall)
For each candidate that has a DOI but NO `pdf_path` (i.e., arXiv download was not available or failed):
1. Call `mcp__unpaywall__unpaywall_get_fulltext_links` with the candidate's DOI
2. If an open-access link is returned:
   a. Call `mcp__unpaywall__unpaywall_fetch_pdf_text` with the DOI
   b. Write the extracted text to `{workspace}/papers/{canonical_id}.txt` (replace `/` and `:` in the ID with `_`)
   c. Update the candidate's `pdf_path` field
3. If no open-access link: skip (paper remains abstract-only)

Log every Unpaywall attempt to `{workspace}/logs/download-log.jsonl`:
```json
{"paper_id": "{id}", "doi": "{doi}", "source": "unpaywall", "timestamp": "{ISO-8601}", "status": "success|no_oa|error", "error_message": null}
```

Pace Unpaywall calls at 1 per second (Unpaywall's rate limit is 100K/day but requests politeness). If rate-limited, apply the same backoff procedure as arXiv.

**Note:** This step only runs if the Unpaywall MCP is available. If `mcp__unpaywall__unpaywall_get_fulltext_links` is not in the tool list, skip this step entirely and log:
```json
{"timestamp": "{ISO-8601}", "event": "unpaywall_unavailable", "phase": 1, "details": {"reason": "MCP not configured"}}
```
```

- [ ] **Step 3: Update Step 8 (Report) to include Unpaywall stats**

Replace the existing `Papers downloaded: {N}` line with:
```markdown
- Papers downloaded (arXiv): {N}
- Papers downloaded (Unpaywall): {N}
- Papers with full text: {N} / {total candidates}
```

- [ ] **Step 4: Commit**

```bash
git -C /home/melek/workshop/scholar add runbooks/search.md
git -C /home/melek/workshop/scholar commit -m "feat: add Unpaywall download step to search runbook"
```

### Task 7: Update Extract Runbook

**Files:**
- Modify: `scholar/runbooks/extract.md`

- [ ] **Step 1: Replace Step 4A with section-guided extraction**

Replace the current Step 4A ("Read paper content") with:

```markdown
**A. Read paper content and prepare extraction context:**
- Check `{workspace}/papers/{paper_id}.*` (replace `/` and `:` with `_`)
- If text file exists (full text available):
  1. Run: `python3 {PLUGIN_DIR}/lib/cli.py parse-sections --file {workspace}/papers/{paper_id}.txt`
  2. This returns a JSON array of sections with headings, levels, and character counts
  3. Note the document structure for use in field extraction below
  4. Set `source = "full_text"`
- If no text file: use abstract + metadata from the paper's record in included.jsonl
  1. Set `source = "abstract"`
```

- [ ] **Step 2: Update Step 4B with section-guided field extraction**

Replace the current Step 4B ("Extract each schema field") with:

```markdown
**B. Extract each schema field:**
For each field in the extraction schema:

**If source == "full_text" (section-guided extraction):**
1. Run: `python3 {PLUGIN_DIR}/lib/cli.py parse-sections --file {workspace}/papers/{paper_id}.txt --field {field_name}`
2. This returns focused context: only the sections most likely to contain information for this field
3. Read the returned context (typically 1-3 sections, much smaller than the full paper)
4. Extract the value from the focused context
5. Record the section heading(s) used as `source_location`
6. Assess confidence: high (explicit statement in relevant section), medium (inferred from context), low (field not found in expected sections, fell back to full document)

**If source == "abstract" (abstract-only extraction):**
1. Read abstract + metadata
2. Extract what's available
3. Record source_location as "abstract"
4. Confidence ceiling is "medium" for most fields (abstract rarely contains full detail)

Record each extraction:
```json
{
  "field_name": "{name}",
  "value": "{extracted value}",
  "source_location": "{section heading(s) or 'abstract'}",
  "confidence": "high|medium|low"
}
```
```

- [ ] **Step 3: Add a note about extraction quality tiers**

Add after Step 4D, before Step 5:

```markdown
**Extraction quality note:**
Papers with full text (arXiv + Unpaywall downloads) produce richer extractions with higher confidence. Papers with abstracts only have a confidence ceiling of "medium" and may have empty values for detail-oriented fields (methodology specifics, exact results, limitations). This is expected and honest — the synthesis agent accounts for the `source` field when weighting findings.
```

- [ ] **Step 4: Commit**

```bash
git -C /home/melek/workshop/scholar add runbooks/extract.md
git -C /home/melek/workshop/scholar commit -m "feat: section-guided extraction in extract runbook"
```

### Task 8: Update SKILL.md Allowed Tools

**Files:**
- Modify: `scholar/skills/research/SKILL.md` (line 5)
- Modify: `scholar/skills/continue/SKILL.md` (line 5)

- [ ] **Step 1: Add Unpaywall tools to research SKILL.md**

In the `allowed-tools` header, add after the arXiv tools. The MCP server name prefix depends on how the Unpaywall MCP is registered — use `unpaywall` as the server name when configuring (the npm package is `unpaywall-mcp` but the server name in claude config is user-controlled):
```
mcp__unpaywall__unpaywall_search_titles, mcp__unpaywall__unpaywall_get_by_doi, mcp__unpaywall__unpaywall_get_fulltext_links, mcp__unpaywall__unpaywall_fetch_pdf_text
```

- [ ] **Step 2: Add same tools to continue SKILL.md**

Same change.

- [ ] **Step 3: Add Unpaywall availability check to Phase 1 pre-flight**

In the SKILL.md section that checks MCP availability before Phase 1, add:
```
- Unpaywall MCP (optional): attempt `mcp__unpaywall__unpaywall_get_by_doi` with a known DOI (e.g., `10.1145/3359591.3359735`). If unavailable, log and continue (papers with DOIs but no arXiv ID will remain abstract-only).
```

- [ ] **Step 4: Commit**

```bash
git -C /home/melek/workshop/scholar add skills/research/SKILL.md skills/continue/SKILL.md
git -C /home/melek/workshop/scholar commit -m "feat: add Unpaywall MCP tools to allowed-tools"
```

---

## Verification Checklist

After all tasks:

- [ ] `dafny verify scholar/lib/verified/section_parser.dfy` passes
- [ ] `python3 -m pytest scholar/tests/test_section_parser.py -v` all green
- [ ] `python3 -m lib.cli parse-sections --file /tmp/test_paper.txt` returns valid JSON
- [ ] `python3 -m lib.cli parse-sections --file /tmp/test_paper.txt --field methodology` returns focused context
- [ ] Design spec §9 dependencies table includes Unpaywall
- [ ] Search runbook has Step 6b (Unpaywall, after enrichment)
- [ ] Extract runbook Step 4A/4B references parse-sections CLI
- [ ] Both SKILL.md files include Unpaywall tools
- [ ] No regressions: `python3 -m lib.cli metrics --workspace ~/research/formal-methods-nondeterministic-oracles/` still works
