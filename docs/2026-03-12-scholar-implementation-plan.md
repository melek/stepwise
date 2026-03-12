# Scholar Plugin Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Claude Code plugin that conducts autonomous systematic literature reviews following the Kitchenham protocol.

**Architecture:** A Claude Code plugin with 3 skills (research, continue, status) that orchestrate 5 phase-specific agents via runbooks. All state lives in a workspace directory under `~/research/`. Agents are stateless workers; the orchestrator manages phase transitions deterministically.

**Tech Stack:** Claude Code plugin system (SKILL.md files), MCP servers (Semantic Scholar, arXiv, Zotero), markdown runbooks, JSONL data files.

**Spec:** `docs/2026-03-12-scholar-design.md` (v1.2)

---

## File Structure

```
scholar/
  .claude-plugin/
    plugin.json                    # Plugin metadata
  skills/
    research/
      SKILL.md                     # Main skill: protocol definition + orchestration loop
    continue/
      SKILL.md                     # Resume from workspace state
    status/
      SKILL.md                     # Report project status
  runbooks/
    search.md                      # Phase 1 agent protocol
    screen.md                      # Phase 2 agent protocol
    snowball.md                    # Phase 3 agent protocol
    extract.md                     # Phase 4 agent protocol
    synthesize.md                  # Phase 5 agent protocol
    postconditions.md              # Postcondition check procedures (shared reference)
  templates/
    protocol-template.md           # Kitchenham protocol template (filled during Phase 0)
    review-template.md             # Literature review document template
  docs/
    2026-03-12-scholar-design.md   # Specification (already exists)
```

**Key design decisions:**
- Runbooks are the core deliverables — they must be precise enough for a cold agent to execute without additional context
- Skills are thin orchestration wrappers that dispatch agents with runbooks
- Templates are starting points filled by the orchestrator/agents during execution
- postconditions.md is a shared reference used by the orchestrator to validate phase completion

---

## Chunk 1: Plugin Scaffold and Templates

### Task 1: Plugin metadata

**Files:**
- Create: `scholar/.claude-plugin/plugin.json`

- [ ] **Step 1: Create plugin.json**

```json
{
  "name": "scholar",
  "version": "0.1.0",
  "description": "Autonomous systematic literature review following the Kitchenham protocol",
  "author": {
    "name": "Melek"
  },
  "license": "MIT"
}
```

- [ ] **Step 2: Commit**

```bash
git add scholar/.claude-plugin/plugin.json
git commit -m "feat: initialize scholar plugin scaffold"
```

---

### Task 2: Protocol template

**Files:**
- Create: `scholar/templates/protocol-template.md`

This template is filled during Phase 0 (interactive with user). It defines every parameter that governs the review. The orchestrator validates completeness before advancing to Phase 1.

- [ ] **Step 1: Write protocol template**

The template must contain all fields from spec §2.2 Phase 0, with placeholder markers for the orchestrator to validate completeness. Every field that the postcondition checker validates must be present.

Reference: spec lines 96-108 (Phase 0 process), lines 556-578 (postcondition checks that reference protocol fields).

Fields required:
- `research_question` — the primary question
- `sub_questions[]` — 1-3 specific sub-questions
- `search_terms{}` — per-database Boolean query strings
- `databases[]` — which databases to search
- `inclusion_criteria[]` — each with id, description, testable condition
- `exclusion_criteria[]` — same structure
- `quality_checklist[]` — quality assessment items
- `extraction_schema[]` — named fields with types
- `bounds.max_results_per_query` — integer
- `bounds.max_snowball_depth` — integer
- `bounds.max_citations_per_paper` — integer
- `bounds.discovery_saturation_threshold` (θ_d) — float
- `bounds.conceptual_saturation_k` (k) — integer
- `bounds.conceptual_saturation_threshold` (θ_c) — float
- `bounds.max_feedback_iterations` — integer (max Phase 4→3 loops)
- `bounds.screening_batch_size` — integer
- `bounds.extraction_batch_size` — integer
- `date_range.start` — year
- `date_range.end` — year
- `language` — string
- `venue_constraints[]` — optional

- [ ] **Step 2: Commit**

```bash
git add scholar/templates/protocol-template.md
git commit -m "feat: add Kitchenham protocol template"
```

---

### Task 3: Review document template

**Files:**
- Create: `scholar/templates/review-template.md`

- [ ] **Step 1: Write review template**

Follows the structure from spec §6 (lines 593-639). The synthesis agent fills this template. Section headers are fixed; content is generated.

- [ ] **Step 2: Commit**

```bash
git add scholar/templates/review-template.md
git commit -m "feat: add literature review document template"
```

---

## Chunk 2: Postconditions and Orchestrator Skills

### Task 4: Postcondition check procedures

**Files:**
- Create: `scholar/runbooks/postconditions.md`

- [ ] **Step 1: Write postcondition procedures**

This file defines the exact checks the orchestrator performs after each phase. It is referenced by the `research` and `continue` skills. Each check must be mechanically executable by reading workspace files — no inference.

Reference: spec §5.3 (lines 553-578).

For each phase (1-5), define:
- What files to read
- What conditions to check (with exact field references)
- What constitutes pass vs fail
- What the orchestrator should do on failure (retry vs diagnostic)
- How to compute saturation metrics (discovery and conceptual)

Also include the phase transition decision table from spec §2.3 (lines 290-298), including the Phase 4→3 feedback loop and the Phase 2 diagnostic transition.

- [ ] **Step 2: Commit**

```bash
git add scholar/runbooks/postconditions.md
git commit -m "feat: add postcondition check procedures"
```

---

### Task 5: Research skill (main orchestrator)

**Files:**
- Create: `scholar/skills/research/SKILL.md`

- [ ] **Step 1: Write the research skill**

This is the primary entry point. It handles:

1. **New project initialization:**
   - Accept research question from user (passed as argument or asked interactively)
   - Create workspace at `~/research/{project-slug}/`
   - Create directory structure (data/, logs/, papers/)
   - Initialize `state.json` (spec §3.2, lines 334-364)
   - Run Phase 0 interactively: use the protocol template, refine question with user, fill all fields, get user approval
   - Set `protocol_approved: true`, advance to Phase 1

2. **Autonomous execution loop (Phases 1-5):**
   - For current phase: set `phase_status: in_progress`, log phase_start to phase-log.jsonl
   - Dispatch appropriate agent with: runbook path, workspace path, protocol path
   - On agent completion: run postcondition checks (reference postconditions.md)
   - On postcondition pass: update state.json, log transition, print one-line progress, advance
   - On postcondition fail: retry once, then fail with reason in state.json
   - Handle Phase 4→3 feedback loop (max iterations from protocol bounds)
   - Handle Phase 2 empty-included diagnostic transition
   - On Phase 5 completion: print full statistics summary

Frontmatter:
```yaml
---
name: research
description: Start a new systematic literature review. Refines research question into protocol, then executes autonomous multi-phase review.
argument-hint: "[research question in quotes]"
allowed-tools: Read, Write, Edit, Bash, Glob, Grep, Agent, ToolSearch, mcp__semantic-scholar__search_paper, mcp__semantic-scholar__get_paper, mcp__semantic-scholar__get_authors, mcp__arxiv__search_papers, mcp__arxiv__download_paper, mcp__arxiv__read_paper, mcp__arxiv__list_papers, mcp__zotero__zotero_search, mcp__zotero__zotero_get_item, mcp__zotero__zotero_list_collections, mcp__zotero__zotero_get_collection_items
---
```

The skill body must include:
- Workspace initialization procedure with exact directory/file creation commands
- Phase 0 interactive protocol: questions to ask, how to fill the template, validation checklist
- The orchestration loop: dispatch → postcondition → transition logic
- Progress reporting format
- Error handling for each failure mode

- [ ] **Step 2: Commit**

```bash
git add scholar/skills/research/SKILL.md
git commit -m "feat: add research skill (main orchestrator)"
```

---

### Task 6: Continue skill

**Files:**
- Create: `scholar/skills/continue/SKILL.md`

- [ ] **Step 1: Write the continue skill**

Resumes an existing review from workspace state. Logic:

1. Accept project slug as argument or list existing projects in `~/research/`
2. Read `state.json` from workspace
3. Determine next action based on `current_phase` and `phase_status`:
   - `completed` → advance to next phase, enter orchestration loop
   - `in_progress` → re-run current phase (interrupted)
   - `failed` → report failure reason, offer to retry
   - `needs_protocol_revision` → re-enter Phase 0 interactively
4. Enter the same orchestration loop as the research skill (Phases 1-5)

Frontmatter: same allowed-tools as research skill, argument-hint: `"[project-slug]"`

- [ ] **Step 2: Commit**

```bash
git add scholar/skills/continue/SKILL.md
git commit -m "feat: add continue skill for review resumption"
```

---

### Task 7: Status skill

**Files:**
- Create: `scholar/skills/status/SKILL.md`

- [ ] **Step 1: Write the status skill**

Read-only reporting. Logic:

1. Accept project slug or list all projects in `~/research/`
2. Read `state.json`, protocol.md, and log files
3. Report: current phase, phase status, key metrics from state.json, last phase-log entry, next action
4. If project is complete: report final statistics (total candidates, included, concepts, themes)

Frontmatter: allowed-tools limited to `Read, Glob, Grep`, argument-hint: `"[project-slug]"`

- [ ] **Step 2: Commit**

```bash
git add scholar/skills/status/SKILL.md
git commit -m "feat: add status skill for project reporting"
```

---

## Chunk 3: Phase Agent Runbooks (Search, Screen)

### Task 8: Search agent runbook (Phase 1)

**Files:**
- Create: `scholar/runbooks/search.md`

- [ ] **Step 1: Write search runbook**

The search agent executes Phase 1: database search and candidate collection. Zero inference.

Reference: spec §2.2 Phase 1 (lines 114-139), §4.3 file ownership (line 518), §3.4 deduplication (lines 369-377), §5.4 rate limits (lines 583-585).

Runbook must specify:
1. Read `protocol.md` — extract search terms, databases, date range, max_results_per_query
2. For each database × query combination:
   - Call appropriate MCP tool (`mcp__semantic-scholar__search_paper` or `mcp__arxiv__search_papers`)
   - Log query to `logs/search-log.jsonl` with: query, database, timestamp, result_count
   - Parse results into candidate records (spec §3.5 candidate schema, lines 382-401)
3. Deduplication procedure:
   - Canonical ID resolution: DOI > arXiv ID > S2 ID
   - Cross-reference all three ID fields
   - Title similarity check (normalized Levenshtein > 0.9) for papers without matching IDs
   - Keep record with more metadata, note `also_found_via`
4. For arXiv papers: download via `mcp__arxiv__download_paper`, read via `mcp__arxiv__read_paper`, write to `papers/{canonical_id}.txt`
5. Fetch additional metadata via `mcp__semantic-scholar__get_paper` for papers found on arXiv only
6. Write all candidates to `data/candidates.jsonl`
7. Report: number of queries executed, total results, unique candidates after dedup

Rate limit handling: exponential backoff on 429 responses (2s, 4s, 8s, 16s, 32s max), log to phase-log.jsonl.

- [ ] **Step 2: Commit**

```bash
git add scholar/runbooks/search.md
git commit -m "feat: add search agent runbook (Phase 1)"
```

---

### Task 9: Screen agent runbook (Phase 2)

**Files:**
- Create: `scholar/runbooks/screen.md`

- [ ] **Step 1: Write screening runbook**

The screening agent applies inclusion/exclusion criteria to candidates. Uses inference for criterion evaluation.

Reference: spec §2.2 Phase 2 (lines 143-167), §4.2 inference quarantine (lines 505-512), §4.3 file ownership (line 519).

Runbook must specify:
1. Read `protocol.md` — extract inclusion criteria, exclusion criteria
2. Read `data/candidates.jsonl` — get unscreened papers (those without entries in `logs/screening-log.jsonl`)
3. For each candidate (up to `screening_batch_size`):
   a. Present title + abstract
   b. Evaluate each inclusion criterion independently:
      - State the criterion
      - Quote evidence from abstract that supports or refutes it
      - Record: criterion_id, criterion_type, met (yes/no/unclear), evidence, source
   c. Evaluate each exclusion criterion independently (same structure)
   d. Apply deterministic decision rule:
      - All inclusion met AND no exclusion met → include
      - Any exclusion met OR any inclusion not met → exclude
      - Any criterion unclear → flag_for_full_text
   e. For flagged papers: check if PDF exists in `papers/`. If yes, read intro + conclusion, re-evaluate unclear criteria, resolve to include/exclude. If no PDF or still unclear → exclude with `insufficient_evidence`
   f. Write complete evaluation to `logs/screening-log.jsonl`
   g. If decision=include, append to `data/included.jsonl`
4. Report: papers screened, included, excluded, flagged-then-resolved

Inference quarantine: each criterion evaluation is a separate judgment. The decision rule is deterministic. Failed inference → skip paper (record failure, do not guess).

- [ ] **Step 2: Commit**

```bash
git add scholar/runbooks/screen.md
git commit -m "feat: add screening agent runbook (Phase 2)"
```

---

## Chunk 4: Phase Agent Runbooks (Snowball, Extract, Synthesize)

### Task 10: Snowball agent runbook (Phase 3)

**Files:**
- Create: `scholar/runbooks/snowball.md`

- [ ] **Step 1: Write snowball runbook**

The snowball agent follows citation chains from included papers to discover missed papers.

Reference: spec §2.2 Phase 3 (lines 171-201), §4.3 file ownership (line 520), §3.4 deduplication.

Runbook must specify:
1. Read `protocol.md` — extract max_snowball_depth, discovery_saturation_threshold (θ_d), inclusion/exclusion criteria, max_citations_per_paper
2. Read `data/included.jsonl` — these are the seed papers for this iteration
3. Track which papers have already been snowballed (check `logs/snowball-log.jsonl`)
4. For each depth level (1 to max_depth):
   a. For each un-snowballed paper in included.jsonl:
      - Fetch backward citations via `mcp__semantic-scholar__get_paper` with `references` field
      - Fetch forward citations via `mcp__semantic-scholar__get_paper` with `citations` field
      - Log `total_citations_available` vs `citations_retrieved` — note truncation
      - For each discovered paper not in `data/candidates.jsonl`:
        - Fetch metadata
        - Apply inclusion/exclusion criteria (same process as screen agent)
        - Record in `logs/snowball-log.jsonl`
        - If included: append to `data/included.jsonl` and `data/candidates.jsonl`
   b. Compute discovery saturation: |newly_included| / |total_examined| at this depth
   c. Log saturation check to `logs/phase-log.jsonl`
   d. If saturation < θ_d → terminate
   e. Re-read `data/included.jsonl` for next depth level (new inclusions become seeds)
5. Report: depth levels completed, papers examined, papers included, saturation metric

Important: re-read included.jsonl at each depth level. Do not cache.

- [ ] **Step 2: Commit**

```bash
git add scholar/runbooks/snowball.md
git commit -m "feat: add snowball agent runbook (Phase 3)"
```

---

### Task 11: Extract agent runbook (Phase 4)

**Files:**
- Create: `scholar/runbooks/extract.md`

- [ ] **Step 1: Write extraction runbook**

The extraction agent extracts structured data from included papers using the protocol's extraction schema.

Reference: spec §2.2 Phase 4 (lines 205-231), §4.3 file ownership (line 521).

Runbook must specify:
1. Read `protocol.md` — extract extraction_schema (named fields with types)
2. Read `data/included.jsonl` — papers to extract from
3. Read `data/extractions.jsonl` — skip papers already extracted (relevant for Phase 4→3→4 feedback)
4. For each un-extracted paper (up to `extraction_batch_size`):
   a. Read full text: check `papers/{id}.*` for PDF/text. If unavailable, use abstract + metadata.
   b. For each field in extraction_schema:
      - Extract value from paper
      - Record: field_name, value, source_location (page/section or "abstract"), confidence (high/medium/low)
   c. Identify concepts: themes, methods, key findings
      - For each concept: check if it exists in `data/concepts.jsonl`
      - If new: assign concept_id (slug), write definition, record first_seen_in
      - If existing: increment frequency
   d. Write extraction record to `data/extractions.jsonl`
   e. Update `concept-matrix.md`: add row for this paper, mark columns for identified concepts
5. After all extractions: compute conceptual saturation
   - Read `data/concepts.jsonl`, compute Δ(n, k) = |new concepts in last k papers| / |total concepts|
   - Log to `logs/phase-log.jsonl` with event `saturation_check`
6. Report: papers extracted, new concepts found, total concepts, conceptual saturation metric

Inference quarantine: extraction and concept identification use inference. Each field extraction is logged with source location. Confidence reflects whether full text or abstract was available.

- [ ] **Step 2: Commit**

```bash
git add scholar/runbooks/extract.md
git commit -m "feat: add extraction agent runbook (Phase 4)"
```

---

### Task 12: Synthesis agent runbook (Phase 5)

**Files:**
- Create: `scholar/runbooks/synthesize.md`

- [ ] **Step 1: Write synthesis runbook**

The synthesis agent produces the final literature review document.

Reference: spec §2.2 Phase 5 (lines 235-275), §6 output specification (lines 589-640), §4.3 file ownership (line 522).

Runbook must specify:
1. Read all inputs:
   - `protocol.md` — research question, sub-questions
   - `concept-matrix.md` — paper × concept mapping
   - `data/extractions.jsonl` — structured data from each paper
   - `data/included.jsonl` — paper metadata
   - `data/concepts.jsonl` — concept vocabulary
2. Organize concepts into themes:
   - Group related concepts (by co-occurrence in papers, semantic similarity)
   - Name each theme
3. Read `templates/review-template.md` as starting structure
4. Write each section:
   - **Abstract:** 150-300 words summarizing question, method, findings, implications
   - **Introduction:** research question from protocol, motivation, scope
   - **Methodology:** protocol summary with statistics from logs:
     - Count candidates, screened, included, snowballed from data files
     - Compute PRISMA flow numbers
     - Record search dates and databases from search-log
   - **Results §3.1:** PRISMA flow diagram (text-based), statistics table
   - **Results §3.2:** One subsection per theme. For each: synthesize across papers, note consensus/contradictions/gaps. Every claim cites [AuthorYear] with BibTeX keys.
   - **Discussion:** Cross-theme synthesis, gaps, implications, limitations
   - **Conclusion:** Answer each sub-question explicitly (answered/partially/gap)
   - **Appendix A:** Table of all included papers
   - **Appendix B:** Concept matrix (reproduce or reference)
5. Generate `references.bib` — BibTeX entries for all cited papers, using metadata from included.jsonl
6. Write `data/question-answers.jsonl` — map each sub-question to its review section and disposition
7. If Zotero MCP available: check with `mcp__zotero__zotero_list_collections`, create collection named after project slug, add papers
8. Write `review.md` and `references.bib` to workspace root

Citation format: use `[@bibtex_key]` in review.md. BibTeX keys derived from: first_author_lastname + year (e.g., `dijkstra1968`).

- [ ] **Step 2: Commit**

```bash
git add scholar/runbooks/synthesize.md
git commit -m "feat: add synthesis agent runbook (Phase 5)"
```

---

## Chunk 5: Integration and Verification

### Task 13: Install plugin and verify structure

- [ ] **Step 1: Initialize git repo**

```bash
cd /home/melek/workshop/scholar
git init
git add -A
git commit -m "feat: scholar plugin v0.1.0 - autonomous literature review system"
```

- [ ] **Step 2: Install plugin**

```bash
claude plugin add /home/melek/workshop/scholar
```

- [ ] **Step 3: Verify skills load**

```bash
claude /skills
```

Expected: `scholar:research`, `scholar:continue`, `scholar:status` appear in skills list.

- [ ] **Step 4: Verify MCP dependencies available**

Check that semantic-scholar, arxiv, and zotero MCP servers are configured:
```bash
claude mcp list
```

Expected: `semantic-scholar`, `arxiv`, `zotero` all listed.

---

### Task 14: End-to-end smoke test

- [ ] **Step 1: Run `/scholar:research` with a test question**

```
/scholar:research "What approaches exist for formal verification of systems that include nondeterministic components such as neural networks?"
```

Verify:
- Workspace created at `~/research/formal-verification-nondeterministic-components/`
- Protocol definition phase runs interactively
- Protocol template filled correctly
- After protocol approval: Phase 1 search executes
- search-log.jsonl populated
- candidates.jsonl populated

- [ ] **Step 2: If interrupted, verify `/scholar:continue` resumes correctly**

```
/scholar:continue formal-verification-nondeterministic-components
```

Verify: picks up from state.json, runs next phase.

- [ ] **Step 3: Verify `/scholar:status` reports correctly**

```
/scholar:status formal-verification-nondeterministic-components
```

Verify: shows current phase, metrics, next action.

---

## Dependencies Between Tasks

```
Task 1 (plugin.json) ─────────────────────────────────────┐
Task 2 (protocol template) ───────────────────────────────┤
Task 3 (review template) ─────────────────────────────────┤
Task 4 (postconditions) ──────┬───────────────────────────┤
Task 5 (research skill) ──────┤ (references postconditions)│
Task 6 (continue skill) ──────┤                            │
Task 7 (status skill) ────────┘                            │
Task 8 (search runbook) ──────────────────────────────────┤
Task 9 (screen runbook) ──────────────────────────────────┤
Task 10 (snowball runbook) ───────────────────────────────┤
Task 11 (extract runbook) ────────────────────────────────┤
Task 12 (synthesize runbook) ─────────────────────────────┤
Task 13 (install + verify) ───────────────────────────────┘ (all above)
Task 14 (smoke test) ─── depends on Task 13
```

**Parallel tracks:**
- Tasks 1-3 (scaffold + templates): independent, can run in parallel
- Tasks 8-12 (runbooks): independent of each other, depend on Task 4 (postconditions) for reference
- Tasks 5-7 (skills): depend on Task 4, independent of each other
- Task 13: depends on all of 1-12
- Task 14: depends on Task 13

**Recommended execution order for subagent dispatch:**
1. Parallel: Tasks 1, 2, 3
2. Task 4 (postconditions — referenced by everything downstream)
3. Parallel: Tasks 5, 6, 7, 8, 9, 10, 11, 12
4. Task 13 (integration)
5. Task 14 (smoke test — interactive, requires human)
