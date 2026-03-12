# Scholar: Autonomous Literature Review System

## Specification Document

*Version 1.2 — 2026-03-12*

---

## 0. Purpose of This Document

This document specifies the Scholar system: an autonomous literature review tool implemented as a Claude Code plugin. It defines the axioms that govern the system's behavior, the methodology it follows, the formal properties it must satisfy, and the contracts between its components.

Every design decision is derived from the axioms. Where a decision cannot be derived — where it requires judgment — the decision is deferred to the protocol document created at the start of each review, which the human approves before execution begins.

---

## 1. Axioms

These are hard constraints. A system that violates an axiom is incorrect regardless of the quality of its output.

### A1 — Deterministic structure, nondeterministic content

The *process* of conducting a literature review is deterministic: fixed phases, fixed transitions, fixed termination criteria. The *content* produced within each phase involves inference (LLM calls to assess relevance, extract concepts, synthesize findings). The system separates these concerns absolutely. Process logic contains zero inference calls. Content generation is quarantined behind validation gates.

**Formal statement:** Let `P` be the set of process decisions (phase transitions, termination, file routing) and `C` be the set of content decisions (relevance judgments, concept extraction, synthesis). Then `P ∩ C = ∅`. No process decision depends on inference output except through a deterministic validation gate `V: C → {accept, reject}`.

### A2 — The workspace is the complete state

All state resides in the filesystem workspace. There is no implicit state — not in memory, not in conversation context, not in environment variables. An agent with access to the workspace directory and the runbook can reconstruct exactly where the review stands and what to do next.

**Formal statement:** Let `W` be the workspace contents at time `t`, and `R` be the runbook. For any agent `a`, the next correct action is a function `f(W, R)` — independent of `a`'s history, identity, or prior context.

### A3 — Append-only evidence

Every decision is recorded. Records are append-only. No record is modified or deleted during a review. The evidence trail is sufficient to reconstruct the rationale for every inclusion, exclusion, and analytical judgment.

**Formal statement:** Let `L` be the set of log entries at time `t₁` and `L'` be the set at time `t₂ > t₁`. Then `L ⊆ L'`. For every paper `p` in the final review, there exists a chain of log entries `e₁, ..., eₙ ∈ L'` such that `e₁` records `p`'s discovery and `eₙ` records its inclusion with justification.

### A4 — Bounded work per phase

Each phase performs a bounded amount of work, writes its results, and terminates. No phase runs indefinitely. Bounds are set by the protocol (maximum papers per search, maximum snowball depth, maximum extraction batch size) and enforced by the process logic, not by the agent's judgment.

**Formal statement:** For each phase `φ` with bound `b(φ)` defined in the protocol, the number of atomic work units executed in one invocation of `φ` is at most `b(φ)`. The bound is checked by a counter, not estimated by the agent.

### A5 — Saturation is a measured property

The discovery process (Phases 1-3) and the extraction process (Phase 4) each have distinct, computable termination criteria.

**Discovery saturation** governs Phase 3 (snowballing). It measures diminishing returns on finding new *papers*: the ratio of newly-included papers to total papers examined at each depth level. When this ratio falls below threshold `θ_d`, discovery terminates.

**Conceptual saturation** governs whether Phase 4 triggers a return to Phase 3. It measures whether the included corpus covers the conceptual space: the ratio of new concepts introduced by the last `k` extracted papers to the total concept count. If this ratio exceeds threshold `θ_c` after extraction completes, the concept space is still expanding and a new snowball iteration is warranted.

**Formal statements:**

Discovery saturation: Let `included(d)` be papers included at snowball depth `d`, and `examined(d)` be papers examined at depth `d`. Discovery terminates when `|included(d)| / |examined(d)| < θ_d` for protocol-defined `θ_d`, or when `d = max_depth`.

Conceptual saturation: Let `concepts(n)` be the cumulative concept set after extracting `n` papers, and `Δ(n, k) = |concepts(n) \ concepts(n-k)| / |concepts(n)|`. If `Δ(n, k) ≥ θ_c` at Phase 4 completion, transition back to Phase 3 with the new included papers as seeds. Otherwise, proceed to Phase 5.

### A6 — Sovereignty

All data — papers, logs, notes, the review document — resides in the user's filesystem. Papers are downloaded locally when possible (arXiv). Zotero is used as a reference manager, not as primary storage; the workspace is authoritative. Cloud APIs (Semantic Scholar, arXiv) are used for discovery only. No user data is sent to external services except search queries.

### A7 — Reproducibility

Given the same protocol and the same corpus state (which changes over time as new papers are published), two executions of the same review should produce substantially similar results. This is achieved by: recording exact search queries and timestamps, logging every inclusion/exclusion decision with criteria, and making the concept extraction schema explicit in the protocol.

**Caveat:** Full reproducibility is impossible because (a) the corpus changes, (b) inference is nondeterministic, and (c) snowballing traverses a mutable citation graph. The system maximizes reproducibility within these constraints by recording enough state to understand *why* results differ between runs.

---

## 2. Methodology: Kitchenham SLR with Snowball Discovery

The system implements a Systematic Literature Review following the Kitchenham protocol (Kitchenham & Charters, 2007), augmented with Wohlin's snowballing procedure (Wohlin, 2014) as a complementary discovery mechanism.

### 2.1 Phases

The review proceeds through six sequential phases. Each phase has defined inputs, outputs, a termination condition, and a postcondition that must hold before the next phase begins.

```
Phase 0: Protocol Definition
Phase 1: Search
Phase 2: Screening
Phase 3: Snowballing
Phase 4: Data Extraction
Phase 5: Synthesis
```

### 2.2 Phase Specifications

#### Phase 0 — Protocol Definition

**Purpose:** Produce a rigorous, complete research protocol before any search begins. This is the only interactive phase.

**Inputs:** Raw research question from user.

**Process:**
1. Refine the research question into 1-3 specific, answerable sub-questions
2. Define search terms and Boolean query strings per database
3. Define inclusion criteria (explicit, testable conditions)
4. Define exclusion criteria (explicit, testable conditions)
5. Define quality assessment checklist
6. Define concept extraction schema (what data to extract from each paper)
7. Set phase bounds: max papers per search query, max snowball depth, max citations to retrieve per paper (note: Semantic Scholar caps at 500), discovery saturation threshold `θ_d`, conceptual saturation parameters (`k`, `θ_c`), max Phase 4→3 feedback iterations
8. Set date range, language constraints, venue constraints if any

**Outputs:** `protocol.md` — the governing document for the entire review.

**Postcondition:** Protocol contains all fields. Inclusion/exclusion criteria are binary-testable (no subjective judgment required). Concept extraction schema has named fields with types. Bounds are numeric. The human has approved the protocol.

**Inference:** Yes — question refinement and search term generation require inference. This is the one phase where interactive inference is justified because the protocol governs everything downstream.

---

#### Phase 1 — Search

**Purpose:** Execute database searches and collect candidate papers.

**Agent:** Search agent (runbook: `search.md`)

**Inputs:** `protocol.md` (search terms, date range, database list)

**Process:**
1. For each database (Semantic Scholar, arXiv):
   a. Execute each query string from the protocol
   b. Record: query, database, timestamp, result count, paper IDs returned
   c. Deduplicate (see §3.4 Deduplication)
2. Download available PDFs via arXiv MCP, then write content to workspace `papers/` directory (arXiv MCP stores internally; the search agent must read via `read_paper` and write to `papers/{id}.pdf` to satisfy A2)
3. Fetch metadata for all candidates (title, abstract, authors, year, venue, citation count)
4. Write candidate records to `candidates.jsonl`

**Outputs:**
- `search-log.jsonl` — every query executed, parameters, result counts
- `candidates.jsonl` — deduplicated candidate papers with metadata

**Postcondition:** Every query in the protocol has been executed against every specified database. `candidates.jsonl` contains no duplicate DOIs. Every entry has at minimum: id, title, abstract, authors, year.

**Inference:** None. Pure API calls and data assembly.

**Bound:** Protocol-defined maximum results per query. Total candidates unbounded (determined by search results).

---

#### Phase 2 — Screening

**Purpose:** Apply inclusion/exclusion criteria to candidates. Decide which papers enter the review.

**Agent:** Screening agent (runbook: `screen.md`)

**Inputs:** `protocol.md` (inclusion/exclusion criteria), `candidates.jsonl`

**Process:**
For each candidate paper:
1. Evaluate each inclusion criterion against title + abstract. Record: criterion, met (yes/no/unclear), evidence (quoted text).
2. Evaluate each exclusion criterion. Record same.
3. Decision: include (all inclusion criteria met, no exclusion criteria met), exclude (any exclusion criterion met or any inclusion criterion not met), or flag for full-text review (criteria unclear from abstract alone).
4. For flagged papers: if PDF available, read introduction + conclusion and re-evaluate. If PDF unavailable or re-evaluation still unclear, exclude with reasoning `insufficient_evidence`. Every paper must resolve to a binary include/exclude.
5. Write decision + reasoning to `screening-log.jsonl`.

**Outputs:**
- `screening-log.jsonl` — every paper, every criterion evaluation, decision, reasoning
- `included.jsonl` — papers that passed screening (subset of candidates)

**Postcondition:** Every paper in `candidates.jsonl` has at least one entry in `screening-log.jsonl` with a final decision of `include` or `exclude` (papers initially flagged for full-text review will have two entries: the initial `flag_for_full_text` and the resolved decision — both are preserved per A3). Every entry in `included.jsonl` satisfies all inclusion criteria and no exclusion criteria as recorded in its final screening log entry.

**Inference:** Yes — relevance assessment against criteria requires judgment. Quarantined: the agent evaluates criteria one at a time and records evidence. The decision rule (all inclusion met, no exclusion met) is deterministic; only the per-criterion assessment uses inference.

**Bound:** Protocol-defined batch size per invocation. Multiple invocations until all candidates processed.

---

#### Phase 3 — Snowballing

**Purpose:** Discover papers missed by database search by following citation chains from included papers.

**Agent:** Snowball agent (runbook: `snowball.md`)

**Inputs:** `protocol.md` (inclusion/exclusion criteria, snowball depth, saturation params), `included.jsonl`

**Process:**
1. For each paper in `included.jsonl`, retrieve:
   a. Backward citations (papers this paper cites)
   b. Forward citations (papers that cite this paper)
2. For each discovered paper not already in `candidates.jsonl`:
   a. Fetch metadata
   b. Apply inclusion/exclusion criteria (same process as Phase 2)
   c. If included, add to `included.jsonl` and queue for snowballing at next depth level
3. Record: source paper, direction (forward/backward), discovered paper, decision
4. After each depth level: compute discovery saturation metric (included/examined ratio)
5. Terminate when: discovery saturation threshold `θ_d` met OR maximum depth reached
6. Log `total_citations_available` vs `citations_retrieved` for each paper (forward citations may be truncated for highly-cited papers; Semantic Scholar caps nested fields at 500)

**Outputs:**
- `snowball-log.jsonl` — every citation traversal, discovery, decision
- Updated `included.jsonl` — papers discovered via snowballing appended
- Updated `candidates.jsonl` — all discovered papers appended

**Postcondition:** For every paper in `included.jsonl`, backward and forward citations have been examined to the protocol-defined depth or until discovery saturation. Every discovered paper has a screening decision recorded. Discovery saturation metric at termination is below threshold `θ_d`, or maximum depth was reached. Citation truncation events are logged.

**Inference:** Yes — same criterion-based assessment as Phase 2, same quarantine structure.

**Bound:** Protocol-defined maximum snowball depth. Protocol-defined saturation parameters.

---

#### Phase 4 — Data Extraction

**Purpose:** Extract structured data from each included paper according to the concept extraction schema defined in the protocol.

**Agent:** Extraction agent (runbook: `extract.md`)

**Inputs:** `protocol.md` (extraction schema), `included.jsonl`, downloaded PDFs

**Process:**
For each included paper (skip if extraction record already exists in `extractions.jsonl` — relevant during Phase 4→3→4 feedback loops):
1. Read full text (PDF if available, else abstract + metadata)
2. Extract each field defined in the concept extraction schema
3. Record: paper ID, field name, extracted value, source location (page/section), confidence
4. Identify concepts (themes, methods, findings) — add to concept vocabulary
5. Update concept matrix: paper × concept mapping
6. Write extraction record to `extractions.jsonl`

**Outputs:**
- `extractions.jsonl` — structured data per paper per schema field
- `concept-matrix.md` — papers as rows, concepts as columns, cell = relationship
- `concepts.jsonl` — concept vocabulary with definitions, first-seen paper, frequency

**Postcondition:** Every paper in `included.jsonl` has extraction records for every field in the schema. Concept matrix has an entry for every (paper, concept) pair where the concept appears in the paper. No concept appears without a definition.

**Inference:** Yes — extraction and concept identification require comprehension. Quarantined: each extraction is recorded with source location. The concept vocabulary is an evolving artifact that can be reviewed.

**Bound:** Protocol-defined batch size per invocation.

---

#### Phase 5 — Synthesis

**Purpose:** Produce the literature review document.

**Agent:** Synthesis agent (runbook: `synthesize.md`)

**Inputs:** `protocol.md`, `concept-matrix.md`, `extractions.jsonl`, `included.jsonl`, `concepts.jsonl`

**Process:**
1. Organize concepts into themes (clusters of related concepts)
2. For each theme:
   a. Summarize the state of knowledge across included papers
   b. Identify consensus, contradictions, and gaps
   c. Cite specific papers with structured references
3. Write introduction: research question, motivation, scope
4. Write methodology section: protocol summary, search/screening/snowball statistics
5. Write findings: theme-by-theme synthesis
6. Write discussion: gaps identified, implications, limitations of the review itself
7. Write conclusion: answers to research sub-questions
8. Generate BibTeX bibliography from included papers
9. If Zotero MCP is available: export included papers to a Zotero collection named after the project slug. If unavailable: skip (BibTeX file is the canonical bibliography regardless).

**Outputs:**
- `review.md` — the literature review document
- `references.bib` — BibTeX bibliography
- Zotero collection (conditional — only if Zotero MCP available)

**Postcondition:** Every paper in `included.jsonl` is cited at least once in `review.md`. Every concept in `concept-matrix.md` appears in the findings. Every research sub-question from the protocol is addressed in the conclusion (answered, partially answered, or identified as a gap). `references.bib` contains an entry for every cited paper. `question-answers.jsonl` maps each sub-question to the review section addressing it.

**Additional output:** `question-answers.jsonl` — structured mapping enabling the postcondition checker to verify question coverage without semantic inference:
```json
{
  "question": "string (from protocol)",
  "section": "string (review.md section reference)",
  "disposition": "enum: answered | partially_answered | identified_as_gap"
}
```

**Inference:** Yes — synthesis is the core generative task. Quarantined: every claim in the review cites specific papers. The concept matrix provides the structural skeleton; inference fills the prose.

**Bound:** Single invocation. Output length bounded by content, not by arbitrary limit.

---

### 2.3 Phase Transition Protocol

Phase transitions are deterministic. The orchestrator (not any agent) decides transitions by checking postconditions.

```
transition(current_phase, workspace) → next_phase | error

Precondition: postcondition(current_phase, workspace) = true
Postcondition: state.json updated with new phase, timestamp, metrics
```

Transition rules:
- `0 → 1`: Protocol exists and is complete (all required fields present)
- `1 → 2`: All queries executed, candidates.jsonl non-empty
- `2 → 3`: All candidates screened, included.jsonl non-empty
- `2 → diagnostic`: All candidates screened, included.jsonl empty. This is a protocol problem (search terms or criteria too restrictive), not a phase failure. The orchestrator reports: "No papers passed screening. Review protocol criteria and search terms." and sets `phase_status = needs_protocol_revision`. `/scholar:continue` re-enters Phase 0.
- `3 → 4`: Discovery saturation reached or max depth hit, snowball-log complete
- `4 → 3`: Conceptual saturation threshold `θ_c` exceeded (concept space still expanding). New included papers become snowball seeds. Maximum 2 feedback iterations to prevent infinite loops.
- `4 → 5`: All included papers have extraction records, concept matrix built, conceptual saturation below `θ_c` (or feedback iteration limit reached)
- `5 → done`: Review document satisfies postcondition (all papers cited, all questions addressed)

If a postcondition fails, the orchestrator re-runs the current phase (not the next one). If it fails twice, the orchestrator writes the failure to `state.json` and terminates. A subsequent `/scholar:continue` will read the failure state and attempt recovery.

**Progress reporting:** On each phase transition, the orchestrator prints a one-line summary to the terminal: phase completed, key metrics (papers found/screened/included, concepts identified), next phase. On completion, a full statistics summary.

---

## 3. Workspace Specification

### 3.1 Directory Structure

```
~/research/{project-slug}/
  protocol.md              # Research protocol (human-approved, governs the review)
  state.json               # Machine-readable project state
  review.md                # Literature review (final deliverable)
  references.bib           # BibTeX bibliography
  concept-matrix.md        # Concept × paper matrix
  data/
    candidates.jsonl       # All discovered papers (deduplicated)
    included.jsonl         # Papers that passed screening
    extractions.jsonl      # Structured data extracted from papers
    concepts.jsonl         # Concept vocabulary
    question-answers.jsonl # Sub-question → review section mapping (Phase 5)
  logs/
    search-log.jsonl       # Search queries and results
    screening-log.jsonl    # Screening decisions with reasoning
    snowball-log.jsonl     # Citation traversals and discoveries
    phase-log.jsonl        # Phase transitions and orchestrator decisions
  papers/                  # Downloaded PDFs
```

### 3.2 state.json Schema

```json
{
  "project_slug": "string",
  "research_question": "string",
  "created_at": "ISO-8601",
  "updated_at": "ISO-8601",
  "current_phase": "integer (0-5)",
  "phase_status": "enum: pending | in_progress | completed | failed | needs_protocol_revision",
  "failure_reason": "string | null",
  "protocol_approved": "boolean",
  "metrics": {
    "total_candidates": "integer",
    "total_included": "integer",
    "total_excluded": "integer",
    "total_flagged": "integer",
    "snowball_depth_reached": "integer",
    "discovery_saturation": "float | null",
    "conceptual_saturation": "float | null",
    "concepts_count": "integer",
    "extraction_complete_count": "integer"
  },
  "phase_history": [
    {
      "phase": "integer",
      "started_at": "ISO-8601",
      "completed_at": "ISO-8601 | null",
      "agent_id": "string | null",
      "work_units_completed": "integer",
      "notes": "string | null"
    }
  ]
}
```

### 3.3 JSONL Record Schemas

### 3.4 Deduplication

Papers may be discovered from multiple sources (Semantic Scholar, arXiv, snowballing) with different identifiers. The canonical ID is resolved in priority order:

1. DOI (if available) — most stable, cross-database
2. arXiv ID (if available) — stable for preprints
3. Semantic Scholar ID — fallback

Two candidate records refer to the same paper if any of: (a) DOIs match, (b) arXiv IDs match, (c) title similarity exceeds threshold `T=0.9` (normalized Levenshtein). On dedup collision, the record with more metadata is kept; the other's `source` is noted in a `also_found_via` field.

### 3.5 JSONL Record Schemas

**candidates.jsonl / included.jsonl:**
```json
{
  "id": "string (canonical ID: DOI > arXiv ID > S2 ID)",
  "doi": "string | null",
  "arxiv_id": "string | null",
  "s2_id": "string | null",
  "title": "string",
  "abstract": "string",
  "authors": ["string"],
  "year": "integer",
  "venue": "string | null",
  "citation_count": "integer | null",
  "source": "enum: search | snowball_backward | snowball_forward",
  "discovered_at": "ISO-8601",
  "discovered_by_query": "string | null",
  "discovered_from_paper": "string | null",
  "also_found_via": ["string | null"],
  "pdf_path": "string | null",
  "zotero_key": "string | null"
}
```

**screening-log.jsonl:**
```json
{
  "paper_id": "string",
  "timestamp": "ISO-8601",
  "criteria_evaluations": [
    {
      "criterion_id": "string",
      "criterion_type": "enum: inclusion | exclusion",
      "met": "enum: yes | no | unclear",
      "evidence": "string (quoted text from abstract/paper)",
      "source": "enum: abstract | full_text"
    }
  ],
  "decision": "enum: include | exclude | flag_for_full_text",
  "reasoning": "string"
}
```

**snowball-log.jsonl:**
```json
{
  "source_paper_id": "string",
  "direction": "enum: forward | backward",
  "discovered_paper_id": "string",
  "already_known": "boolean",
  "screening_decision": "enum: include | exclude | null",
  "depth_level": "integer",
  "timestamp": "ISO-8601",
  "total_citations_available": "integer | null",
  "citations_retrieved": "integer | null",
  "truncated": "boolean"
}
```

**extractions.jsonl:**
```json
{
  "paper_id": "string",
  "timestamp": "ISO-8601",
  "schema_version": "string",
  "fields": [
    {
      "field_name": "string (from protocol extraction schema)",
      "value": "string",
      "source_location": "string (page, section, or 'abstract')",
      "confidence": "enum: high | medium | low"
    }
  ],
  "concepts_identified": ["string (concept IDs)"]
}
```

**concepts.jsonl:**
```json
{
  "concept_id": "string (slug)",
  "label": "string",
  "definition": "string",
  "first_seen_in": "string (paper_id)",
  "first_seen_at": "ISO-8601",
  "frequency": "integer (papers containing this concept)"
}
```

**phase-log.jsonl:**
```json
{
  "timestamp": "ISO-8601",
  "event": "enum: phase_start | phase_complete | phase_fail | postcondition_check | transition | saturation_check",
  "phase": "integer",
  "details": "object (event-specific data)",
  "saturation_metric": "float | null"
}
```

---

## 4. Agent Contracts

Each agent is a stateless worker. It receives a runbook and a workspace path. It reads what it needs, does bounded work, writes results, and terminates. The orchestrator is responsible for phase transitions and postcondition checks.

### 4.1 General Contract

**Preconditions (all agents):**
- Workspace directory exists and contains `state.json` and `protocol.md`
- `state.json.current_phase` matches the agent's phase
- `state.json.phase_status` is `in_progress`

**Postconditions (all agents):**
- All output files are valid JSONL (one JSON object per line, parseable)
- No existing log entries have been modified or deleted
- New entries appended to the appropriate log files
- Work count recorded for orchestrator to track against bounds

**Invariants:**
- Agent never modifies `state.json` (orchestrator's responsibility)
- Agent never modifies `protocol.md`
- Agent reads `protocol.md` at start and follows it exactly
- Agent writes to its designated output files only

### 4.2 Inference Quarantine Contract

Every agent that uses inference must satisfy:

1. **Separation:** The inference call produces a candidate judgment. A deterministic validation step accepts or rejects it.
2. **Recording:** Every inference call is logged: input (what was sent), output (what was returned), validation result (accepted/rejected), and the final decision.
3. **Fallback:** If inference fails (timeout, malformed response, validation rejection), the agent records the failure and skips the item. It does not guess, retry with weaker constraints, or proceed without the judgment.
4. **Justification:** Every inference call maps to a specific protocol requirement. No exploratory or speculative inference.

### 4.3 Agent-Specific File Ownership

| Agent | Reads | Writes (append-only) | Writes (create/update) |
|-------|-------|---------------------|----------------------|
| Search | protocol.md | search-log.jsonl, candidates.jsonl | — |
| Screen | protocol.md, candidates.jsonl | screening-log.jsonl | included.jsonl |
| Snowball | protocol.md, included.jsonl (re-read at each depth level), candidates.jsonl | snowball-log.jsonl, screening-log.jsonl | included.jsonl (append), candidates.jsonl (append) |
| Extract | protocol.md, included.jsonl, papers/ | extractions.jsonl, concepts.jsonl | concept-matrix.md |
| Synthesize | protocol.md, concept-matrix.md, extractions.jsonl, included.jsonl, concepts.jsonl | — | review.md, references.bib |

---

## 5. Orchestrator Specification

The orchestrator is the only component that manages phase transitions and project state. It is deterministic — no inference calls.

### 5.1 Responsibilities

1. Create workspace and initialize `state.json` on new project
2. Run Phase 0 (protocol definition) interactively with the user
3. For Phases 1-5: dispatch the appropriate agent, wait for completion, check postcondition, transition or retry
4. Compute saturation metrics between Phase 3 invocations
5. Handle failures: record in `state.json`, terminate cleanly
6. On `/scholar:continue`: read `state.json`, determine next action, resume

### 5.2 Execution Modes

**Sequential sub-agents (primary):**
The orchestrator dispatches one agent at a time via the Agent tool. Each agent runs in a fresh context with only its runbook and workspace path. The orchestrator checks postconditions between dispatches. This is the baseline execution model that must always work.

**Agent teams (when available):**
If the `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS` feature flag is set, the orchestrator may spawn agents as teammates for phases where parallel work is safe (e.g., Phase 1 search across multiple databases). Each teammate receives its runbook, workspace path, and a tightly scoped task. Teammates own distinct output files — no shared writes. The orchestrator monitors completion via the team task list.

Agent teams are an optimization. The workspace structure is identical in both modes. Correctness does not depend on parallelism.

### 5.3 Postcondition Checker

The orchestrator runs postcondition checks as deterministic functions over the workspace. No inference.

```
check_postcondition(phase, workspace_path) → {satisfied: bool, failures: [string]}

Phase 1: ∀ query ∈ protocol.queries: ∃ entry ∈ search-log where entry.query = query
         |candidates.jsonl| > 0
         no duplicate canonical IDs in candidates.jsonl (see §3.4)

Phase 2: ∀ paper ∈ candidates.jsonl: ∃ entry ∈ screening-log
           where entry.paper_id = paper.id AND entry.decision ∈ {include, exclude}
         (flagged papers have two entries: initial flag + resolved decision; both preserved)
         (note: included.jsonl may be empty — triggers diagnostic transition, not retry)

Phase 3: discovery_saturation < θ_d OR snowball_depth = max_depth
         ∀ paper ∈ included.jsonl (at phase start): citations examined
         citation truncation events logged where applicable

Phase 4: ∀ paper ∈ included.jsonl: ∃ extraction ∈ extractions.jsonl
         |concepts.jsonl| > 0
         concept-matrix.md exists and is non-empty
         conceptual_saturation computed → drives transition to Phase 5 or back to Phase 3

Phase 5: ∀ paper ∈ included.jsonl: paper.id appears in review.md
         ∀ question ∈ protocol.questions: question text appears in review.md §5 (Conclusion)
         synthesis agent produces question-answers.jsonl mapping each sub-question
           to the section that addresses it (structural check, not semantic)
         |references.bib entries| = |unique citations in review.md|
```

---

### 5.4 Rate Limit Handling

Agents must handle HTTP 429 (rate limit) responses from Semantic Scholar and arXiv APIs with exponential backoff (initial 2s, max 60s, max 5 retries). Rate limit events are logged to `phase-log.jsonl` with event type `rate_limit`. If retries are exhausted, the agent records the incomplete work and terminates; the orchestrator detects incomplete work via postcondition failure and retries the phase.

---

## 6. Output Specification: The Literature Review

The final `review.md` follows a structure derived from Kitchenham's reporting guidelines:

```markdown
# {Title}

## Abstract
150-300 words. Research question, method, key findings, implications.

## 1. Introduction
- Research question and motivation
- Scope and boundaries
- Structure of the review

## 2. Methodology
- Protocol summary (search strategy, databases, date range)
- Inclusion/exclusion criteria
- Screening process and statistics
- Snowballing procedure and saturation metrics
- Data extraction schema
- Threats to validity of this review

## 3. Results
### 3.1 Search and Screening Results
- PRISMA-style flow: candidates → screened → included → snowballed
- Statistics table

### 3.2 Findings by Theme
- One subsection per theme (derived from concept clusters)
- Within each theme: state of knowledge, consensus, contradictions, gaps
- Every claim cites specific papers

## 4. Discussion
- Synthesis across themes
- Identified research gaps
- Implications for practice
- Limitations of this review

## 5. Conclusion
- Answers to each research sub-question
- Recommended directions

## References
(BibTeX-keyed citations, full bibliography in references.bib)

## Appendix A: Included Papers
Table: ID, Title, Authors, Year, Venue, Relevance

## Appendix B: Concept Matrix
(Reproduced or referenced from concept-matrix.md)
```

---

## 7. Properties the System Must Satisfy

These are verifiable properties — testable assertions about the system's behavior.

**P1 — Completeness:** Every paper in `included.jsonl` is cited in `review.md`. Every research question is addressed.

**P2 — Traceability:** For every claim in `review.md`, there exists a chain: claim → cited paper → extraction record → screening decision → search query or snowball traversal. The chain is reconstructable from the JSONL logs alone.

**P3 — Reproducibility of process:** Given `protocol.md` and the logs, an independent reviewer can verify that every inclusion/exclusion decision followed the criteria, even if they disagree with the criteria themselves.

**P4 — Resumability:** For any workspace state, `/scholar:continue` produces the correct next action without external context. Formally: `next_action(state.json, protocol.md, workspace_contents) → deterministic`.

**P5 — Monotonicity:** Log files only grow. `|L(t₂)| ≥ |L(t₁)|` for all `t₂ > t₁`. No evidence is destroyed.

**P6 — Boundedness:** Each phase invocation performs at most `b(φ)` work units, where `b` is defined in the protocol. The system terminates.

**P7 — Sovereignty:** No file in the workspace is stored on or transmitted to an external service, except: (a) search queries sent to Semantic Scholar/arXiv APIs, (b) paper metadata sent to Zotero for collection management.

---

## 8. What This System Does Not Do

Explicit scope exclusions to prevent creep:

- **Does not evaluate paper quality.** Quality assessment is noted in the protocol but applied by the screening agent as binary criteria, not as a scoring system. Papers are in or out.
- **Does not generate novel research questions.** The research question comes from the human. The system refines it for specificity, not for novelty.
- **Does not perform meta-analysis.** No statistical aggregation of results across studies. This is a narrative/thematic synthesis.
- **Does not replace human judgment on protocol.** The protocol is approved by the human before execution. The system follows it; it does not override it.
- **Does not store conversation state.** Agent context is ephemeral. The workspace is the record.

---

## 9. Dependencies

| Dependency | Purpose | Required | Fallback |
|-----------|---------|----------|----------|
| Semantic Scholar MCP | Paper search, metadata, citation graph | Yes (for discovery) | arXiv-only search (degraded coverage) |
| arXiv MCP | Paper search, PDF download | Yes (for full text) | Metadata-only review (degraded extraction) |
| Zotero MCP | Reference management, collection export | No | BibTeX file only, no Zotero sync |
| Claude Code Agent tool | Sub-agent dispatch | Yes | Single-agent sequential execution |
| Agent teams (experimental) | Parallel agent dispatch | No | Sequential sub-agents |

---

## 10. Relationship to Dijkstra's Principles

This system treats inference the way Dijkstra's school treats I/O from an untrusted device:

1. **Quarantine.** Inference output enters through defined gates and is validated before affecting system state.
2. **Nondeterministic refinement.** The agent produces a candidate judgment; deterministic logic decides whether to accept it. The system is correct for *all possible* agent outputs that pass validation.
3. **Compositional verification.** Each phase satisfies its postcondition independently. The orchestrator composes phases; if each postcondition holds, the system postcondition holds.
4. **Separation of mechanism and policy.** Process logic (mechanism) is deterministic. Content judgments (policy) use inference but are recorded and auditable.

Where this system falls short of Dijkstra's standard: the inference quarantine gates are not formally verified. The postcondition checks are structural (does the file exist, does it have the right fields) rather than semantic (is the content correct). Full formal verification of a system that includes LLM inference is an open research problem — and, notably, exactly the kind of question this system is designed to help investigate.
