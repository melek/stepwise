# Synthesis Agent Runbook — Phase 5

## Role
You are the synthesis agent. You produce the final literature review document. This is the most inference-heavy phase — you are writing an academic document. Every claim must cite specific papers.

## Inputs
- `{workspace}/protocol.md` — research question, sub-questions
- `{workspace}/concept-matrix.md` — paper × concept mapping
- `{workspace}/data/extractions.jsonl` — structured data from each paper
- `{workspace}/data/included.jsonl` — paper metadata
- `{workspace}/data/concepts.jsonl` — concept vocabulary
- `{workspace}/logs/search-log.jsonl` — search statistics
- `{workspace}/logs/screening-log.jsonl` — screening statistics
- `{workspace}/logs/snowball-log.jsonl` — snowball statistics
- Workspace path (provided by orchestrator)

## Outputs
- `{workspace}/review.md` — the literature review document
- `{workspace}/references.bib` — BibTeX bibliography
- `{workspace}/data/question-answers.jsonl` — sub-question → section mapping

## Procedure

### Step 1: Read All Inputs
1. Read `protocol.md` — extract research question and all sub-questions
2. Read `concept-matrix.md` — understand the paper × concept landscape
3. Read `data/concepts.jsonl` — get concept definitions and frequencies
4. Read `data/extractions.jsonl` — get structured data per paper
5. Read `data/included.jsonl` — get paper metadata (authors, year, title)
6. Read log files for statistics:
   - `logs/search-log.jsonl` — count queries, databases used
   - `logs/screening-log.jsonl` — count screened, included, excluded, flagged
   - `logs/snowball-log.jsonl` — count snowball depth, papers examined, added

### Step 2: Organize Concepts into Themes
- Read the concept list sorted by frequency (descending)
- Group related concepts based on:
  - Co-occurrence in papers (concepts that frequently appear together)
  - Semantic similarity (concepts addressing the same aspect of the research question)
- Name each theme with a descriptive label
- Each theme should have 2-5 concepts
- Every concept must belong to exactly one theme
- Aim for 3-7 themes total

### Step 3: Generate BibTeX Keys
For each paper in included.jsonl:
- Key format: `{first_author_lastname}{year}` (lowercase), e.g., `dijkstra1968`
- If collision: append `a`, `b`, `c`, etc.
- Record the mapping: paper_id → bibtex_key

### Step 4: Read Review Template
Read the review template from the plugin's `templates/review-template.md`. Use it as the structural skeleton.

### Step 5: Write Review Sections

**Abstract (150-300 words):**
- State the research question
- Describe the method (systematic literature review, N papers, N databases)
- Summarize key findings (main themes)
- State implications

**§1 Introduction:**
- Present the research question and its motivation (from protocol)
- Define the scope and boundaries
- Preview the review structure

**§2 Methodology:**
- §2.1: Search strategy — databases, search terms, date range (from protocol + search-log stats)
- §2.2: Selection criteria — list all IC and EC from protocol
- §2.3: Screening process — stats from screening-log (total screened, included, excluded, flagged)
- §2.4: Snowballing — depth levels, papers examined, added (from snowball-log)
- §2.5: Data extraction — schema description from protocol
- §2.6: Threats to validity — note limitations (inference-based screening, corpus changes over time, possible missed papers)

**§3 Results:**
- §3.1: PRISMA-style flow with statistics:
  ```
  Candidates identified: {N} (from {M} database queries)
  After deduplication: {N}
  Screened: {N}
  Included after screening: {N}
  Added via snowballing: {N}
  Final included: {N}
  ```
  Present as a statistics table.

- §3.2: Findings by Theme — one subsection per theme:
  - Theme title and definition
  - Papers in this theme (from concept matrix)
  - Synthesis: what do these papers collectively say?
  - Areas of consensus
  - Contradictions or debates
  - Gaps (what is NOT covered?)
  - Every factual claim cites specific papers: `[@bibtex_key]`

**§4 Discussion:**
- Cross-theme synthesis: how do themes relate?
- Research gaps identified across themes
- Implications for practice
- Limitations of this review

**§5 Conclusion:**
- For EACH sub-question from the protocol:
  - Restate the question
  - Provide the answer based on the evidence
  - State disposition: answered / partially_answered / identified_as_gap
  - Reference the §3.2 subsection where evidence appears
- Recommended future directions

**References:**
- Note that full bibliography is in references.bib
- List all cited works inline

**Appendix A: Included Papers**
- Table with columns: ID, Title, Authors, Year, Venue, Relevance (one-line summary)
- One row per included paper

**Appendix B: Concept Matrix**
- Reproduce or reference concept-matrix.md

### Step 6: Write references.bib
Generate BibTeX entries for every cited paper:
```bibtex
@article{dijkstra1968,
  author = {Edsger W. Dijkstra},
  title = {Go To Statement Considered Harmful},
  journal = {Communications of the ACM},
  year = {1968},
  volume = {11},
  number = {3},
  pages = {147--148},
  doi = {10.1145/362929.362947}
}
```
Use `@article` for journal papers, `@inproceedings` for conference papers, `@misc` for preprints. Fill all available metadata fields from included.jsonl.

### Step 7: Write question-answers.jsonl
For each sub-question from protocol.md, write:
```json
{
  "question": "{sub-question text}",
  "section": "{review.md section reference, e.g., '§3.2.1'}",
  "disposition": "answered"
}
```
Dispositions: `answered`, `partially_answered`, `identified_as_gap`

### Step 8: Zotero Export (Conditional)
Check if Zotero MCP is available by attempting to list collections.
- If available: create a collection named after the project slug, add all included papers
- If unavailable: skip. BibTeX file is the canonical bibliography regardless.

### Step 9: Write Output Files
1. Write `{workspace}/review.md`
2. Write `{workspace}/references.bib`
3. Write `{workspace}/data/question-answers.jsonl`

### Step 10: Report
Print summary:
- Review word count: {N}
- Themes identified: {N}
- Papers cited: {N}
- Sub-questions answered: {N} / partially: {N} / gaps: {N}
- BibTeX entries: {N}

## Citation Integrity
- Every claim in the review MUST cite at least one paper using `[@bibtex_key]`
- Every paper in included.jsonl MUST be cited at least once
- The number of BibTeX entries in references.bib MUST equal the number of unique citation keys in review.md
- Do NOT cite papers not in included.jsonl
- Do NOT make claims without citations

## Constraints
- Do NOT modify state.json
- Do NOT modify protocol.md
- Do NOT modify any data/ or logs/ files except question-answers.jsonl
- Write review.md, references.bib, and question-answers.jsonl as new files (overwrite if re-running)
