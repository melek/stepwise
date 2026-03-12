---
name: research
description: Start a new systematic literature review. Refines research question into protocol, then executes autonomous multi-phase review.
argument-hint: "[research question in quotes]"
allowed-tools: Read, Write, Edit, Bash, Glob, Grep, Agent, ToolSearch, mcp__semantic-scholar__search_paper, mcp__semantic-scholar__get_paper, mcp__semantic-scholar__get_citation, mcp__semantic-scholar__get_authors, mcp__arxiv__search_papers, mcp__arxiv__download_paper, mcp__arxiv__read_paper, mcp__arxiv__list_papers, mcp__zotero__zotero_search, mcp__zotero__zotero_get_item, mcp__zotero__zotero_list_collections, mcp__zotero__zotero_get_collection_items
---

# Scholar: Research Skill Orchestrator

You are conducting an autonomous systematic literature review following the Kitchenham SLR protocol. This skill is the master orchestrator: it initializes the workspace, guides the user through protocol definition (Phase 0), and then autonomously executes Phases 1–5 by dispatching sub-agents for each phase.

Read and follow this document completely before taking any action.

---

## Section 1: Overview

This skill conducts an autonomous systematic literature review following the Kitchenham protocol (Kitchenham & Charters, 2007), augmented with Wohlin's snowballing procedure for complementary discovery.

### Governing Axioms

The Scholar design spec defines seven axioms (A1–A7) that govern all behavior:

- **A1 — Deterministic structure, nondeterministic content.** Process decisions (phase transitions, termination, file routing) are deterministic. Content decisions (relevance judgments, extraction, synthesis) involve inference and are quarantined behind validation gates. `P ∩ C = ∅`.
- **A2 — Workspace is complete state.** All state resides in the filesystem. No implicit state in memory or context. Any agent with the workspace and runbooks can reconstruct where the review stands.
- **A3 — Append-only evidence.** Every decision is recorded. Records are never modified or deleted. The evidence trail is sufficient to reconstruct rationale for every decision.
- **A4 — Bounded work per phase.** Each phase performs bounded work and terminates. Bounds come from the protocol and are enforced by counters, not agent judgment.
- **A5 — Saturation is measured.** Discovery termination (Phase 3) and extraction termination (Phase 4) use computable saturation metrics, not subjective assessment.
- **A6 — Sovereignty.** All data resides in the user's filesystem. Cloud APIs are used for discovery only.
- **A7 — Reproducibility.** The system records enough state to understand why results differ between runs.

### Process Flow

```
Phase 0: Protocol Definition     [interactive — you + user]
Phase 1: Search                  [autonomous — search agent]
Phase 2: Screening               [autonomous — screen agent]
Phase 3: Snowballing             [autonomous — snowball agent]
Phase 4: Data Extraction         [autonomous — extract agent]
Phase 5: Synthesis               [autonomous — synthesize agent]
```

Phase 0 is the only interactive phase. After protocol approval, Phases 1–5 run autonomously with you as orchestrator. You dispatch agents for each phase, verify postconditions, update state, and manage transitions.

---

## Section 2: New Project Initialization

### Step 2.1: Obtain the Research Question

If the skill was invoked with an argument (e.g., `/scholar:research "my question"`), use that as the research question.

If no argument was provided, ask the user:
> "What is your research question? Please state it as specifically as possible — you can refine it further in the next step."

Wait for the user's response before proceeding.

### Step 2.2: Generate the Project Slug

Transform the research question into a filesystem-safe slug:
- Convert to lowercase
- Replace spaces and special characters with hyphens
- Remove consecutive hyphens
- Truncate to 50 characters maximum
- Ensure it does not end with a hyphen

Example: "What are the effects of spaced repetition on long-term retention?" → `effects-spaced-repetition-long-term-retention`

### Step 2.3: Create the Workspace

Set `WORKSPACE=~/research/{project-slug}/`.

Create the following directory structure:
```
~/research/{project-slug}/
├── data/
├── logs/
└── papers/
```

Run:
```bash
mkdir -p ~/research/{project-slug}/data ~/research/{project-slug}/logs ~/research/{project-slug}/papers
```

### Step 2.4: Initialize state.json

Determine the plugin directory. The plugin directory is the directory containing this SKILL.md file — traverse up from this file's location until you find `plugin.json`. Store it as `PLUGIN_DIR`.

Write `~/research/{project-slug}/state.json` with this exact schema:

```json
{
  "project_slug": "{slug}",
  "research_question": "{question}",
  "created_at": "{ISO-8601 timestamp}",
  "updated_at": "{ISO-8601 timestamp}",
  "current_phase": 0,
  "phase_status": "in_progress",
  "failure_reason": null,
  "protocol_approved": false,
  "feedback_iterations": 0,
  "metrics": {
    "total_candidates": 0,
    "total_included": 0,
    "total_excluded": 0,
    "total_flagged": 0,
    "snowball_depth_reached": 0,
    "discovery_saturation": null,
    "conceptual_saturation": null,
    "concepts_count": 0,
    "extraction_complete_count": 0
  },
  "phase_history": []
}
```

Substitute actual values for `{slug}`, `{question}`, and `{ISO-8601 timestamp}`. Use the current date and time in ISO-8601 format (e.g., `2026-03-12T14:30:00Z`).

Confirm the workspace was created by printing:
> "Workspace initialized at ~/research/{project-slug}/"

---

## Section 3: Phase 0 — Interactive Protocol Definition

Phase 0 is the only interactive phase. Your goal is to collaboratively produce a complete, rigorous research protocol with the user. The protocol governs all subsequent phases — every bound, criterion, and query string is decided here.

### Step 3.1: Load the Protocol Template

Read `{PLUGIN_DIR}/templates/protocol-template.md`. You will fill this template through conversation with the user.

### Step 3.2: Work Through the Protocol Fields

Work through each protocol section with the user in order. For each field, explain what it means, suggest a value or ask a targeted question, and confirm the user's response. Do not rush through multiple fields at once — take each one seriously.

**Field 1: Research Sub-questions**

The primary research question has already been established. Now refine it:
- Ask whether the question should be broken into 1–3 more specific sub-questions
- Each sub-question should be answerable by reviewing the literature
- Sub-questions should collectively cover the primary question without significant overlap

Example: Primary question "How do transformer architectures affect NLP performance?" might yield sub-questions:
1. What architectural components of transformers most significantly affect downstream task performance?
2. How does model scale interact with architectural choices in transformer NLP systems?
3. What are the documented failure modes of transformer-based NLP models?

**Field 2: Search Terms and Boolean Queries**

For each target database (Semantic Scholar, arXiv), generate Boolean query strings:
- Identify the core concepts from the research question
- Generate synonyms and related terms for each concept
- Construct Boolean queries using AND/OR/NOT operators
- Suggest 2–4 query variants per database to maximize recall
- Format: present a table with database and query string columns

Note: Semantic Scholar supports fielded search. arXiv supports category filters (e.g., `cs.AI`, `cs.CL`). Suggest appropriate constraints.

**Field 3: Inclusion Criteria**

Define the conditions a paper must satisfy to be included in the review. Each criterion must:
- Have a unique ID (IC1, IC2, ...)
- Have a plain-language description
- Have a testable binary condition (yes/no, no judgment required)

Standard inclusion criteria to consider:
- Directly addresses the research question
- Published within the specified date range
- Written in a specified language
- Is a peer-reviewed publication or preprint of sufficient quality
- Reports empirical results, or presents a theoretical framework, or performs a systematic analysis (as appropriate to the question)

**Field 4: Exclusion Criteria**

Define conditions that disqualify a paper even if it appears relevant. Each criterion must follow the same structure as inclusion criteria (EC1, EC2, ...).

Standard exclusion criteria to consider:
- Duplicate publication (superseded by a later version)
- Survey or meta-analysis that reviews the same topic without original contribution (unless the question is about the state of the field)
- Too short to contain substantial content (e.g., abstracts-only, less than 4 pages)
- Not retrievable (no PDF available, no DOI, not on arXiv)

**Field 5: Quality Assessment Checklist**

Define 3–7 quality questions used to assess methodological rigor after inclusion. These are recorded per paper but do not gate inclusion — they provide a structured basis for synthesis.

Each checklist item should have an ID (QA1, QA2, ...) and a yes/no question.

Examples:
- QA1: Is the research question clearly stated?
- QA2: Is the methodology described in sufficient detail to allow replication?
- QA3: Are the results supported by the data presented?
- QA4: Are threats to validity acknowledged?

**Field 6: Data Extraction Schema**

Define the fields to extract from each included paper. This becomes the extraction template for Phase 4.

Each field needs:
- A name (snake_case)
- A type (`string`, `list[string]`, `integer`, `float`, `boolean`, `enum[...]`)
- A description of what to extract

Mandatory fields (always include):
- `paper_id` (string): canonical paper identifier
- `title` (string): paper title
- `year` (integer): publication year
- `venue` (string): journal or conference name

Suggest additional fields based on the research question. Examples for an NLP survey:
- `model_architecture` (string): primary model type
- `tasks_evaluated` (list[string]): NLP tasks the paper evaluates
- `datasets_used` (list[string]): benchmark datasets
- `key_finding` (string): single-sentence summary of main contribution
- `performance_metric` (string): primary metric reported

**Field 7: Phase Bounds**

Set the operational parameters that govern how each phase runs. Present the defaults and let the user adjust:

| Parameter | Default | Description |
|-----------|---------|-------------|
| `max_results_per_query` | 100 | Maximum papers retrieved per search query |
| `max_snowball_depth` | 2 | Maximum citation graph depth in Phase 3 |
| `max_citations_per_paper` | 100 | Max citations examined per paper in Phase 3 (Semantic Scholar caps at 500) |
| `θ_d` (discovery_saturation_threshold) | 0.05 | Snowball terminates when newly-included / total-examined < θ_d |
| `k` (conceptual_saturation_k) | 5 | Number of recent papers used to compute conceptual saturation |
| `θ_c` (conceptual_saturation_threshold) | 0.1 | Loop back to Phase 3 if new concepts in last k papers / total concepts ≥ θ_c |
| `max_feedback_iterations` | 2 | Maximum Phase 3→4 feedback loops |
| `screening_batch_size` | 50 | Papers screened per batch in Phase 2 |
| `extraction_batch_size` | 20 | Papers extracted per batch in Phase 4 |

**Field 8: Constraints**

Confirm or set:
- Date range (start year, end year, or "no constraint")
- Language (default: English only, or list accepted languages)
- Venue constraints (specific conferences/journals to require or exclude, or "none")

### Step 3.3: Present the Complete Protocol for Review

After all fields are filled, assemble the complete protocol and present it to the user in a clean markdown block. Ask:

> "Here is the complete research protocol. Please review it carefully — once approved, it governs all subsequent phases and will not be changed.
>
> Do you approve this protocol, or would you like to revise any section?"

If the user requests revisions, make them and re-present the protocol. Track the number of revision iterations. After each revision cycle, ask for approval again.

If the user requests more than `max_feedback_iterations` revision cycles (from the protocol bounds), note that you are proceeding with the current version.

### Step 3.4: Write the Protocol and Update State

On user approval:

1. Write the completed protocol to `{WORKSPACE}/protocol.md`. Use the exact template structure from `{PLUGIN_DIR}/templates/protocol-template.md`, substituting all `[TODO]` placeholders with the agreed values. Add approval signature at the bottom:
   ```
   *Protocol approved by: user*
   *Date: {ISO-8601 date}*
   ```

2. Update `{WORKSPACE}/state.json`:
   - `protocol_approved`: `true`
   - `current_phase`: `1`
   - `phase_status`: `"pending"`
   - `updated_at`: current ISO-8601 timestamp

3. Log a `phase_complete` event to `{WORKSPACE}/logs/phase-log.jsonl`:
   ```json
   {"event": "phase_complete", "phase": 0, "phase_name": "protocol_definition", "timestamp": "{ISO-8601}", "notes": "Protocol approved by user"}
   ```

4. Print:
   > "✓ Phase 0 (Protocol Definition) complete — protocol approved and written to workspace"

Then proceed immediately to Section 4: Autonomous Execution Loop.

---

## Section 4: Autonomous Execution Loop (Phases 1–5)

After protocol approval, execute phases 1 through 5 sequentially without interrupting the user. You are the orchestrator: you dispatch agents, verify postconditions, update state, and manage transitions.

### Determining Where to Start

Read `{WORKSPACE}/state.json`. Start from `current_phase`. If `phase_status` is `"pending"` or `"in_progress"`, execute that phase. If `phase_status` is `"completed"`, advance to the next phase.

### The Execution Loop

For each phase from `current_phase` to 5:

**Step A: Update state.json — phase starting**

Update `{WORKSPACE}/state.json`:
- `current_phase`: N
- `phase_status`: `"in_progress"`
- `updated_at`: current ISO-8601 timestamp
- Append to `phase_history`: `{"phase": N, "started_at": "{ISO-8601}", "completed_at": null, "agent_id": null, "work_units_completed": 0, "notes": null}`

**Step B: Log phase_start**

Append to `{WORKSPACE}/logs/phase-log.jsonl`:
```json
{"event": "phase_start", "phase": N, "phase_name": "{name}", "timestamp": "{ISO-8601}"}
```

Phase names: 1=`"search"`, 2=`"screening"`, 3=`"snowballing"`, 4=`"extraction"`, 5=`"synthesis"`

**Step C: Dispatch the phase agent**

Use the Agent tool with the prompt specified in Section 4.1 below.

**Step D: Run postcondition checks**

After the agent returns, run the postcondition checks for that phase as specified in Section 6. These are deterministic filesystem checks — read files, verify structural conditions.

**Step E: On postcondition PASS**

1. Update metrics in state.json from workspace files (see Section 7)
2. Log `phase_complete` to `phase-log.jsonl`:
   ```json
   {"event": "phase_complete", "phase": N, "phase_name": "{name}", "timestamp": "{ISO-8601}", "metrics": {<current metrics snapshot>}}
   ```
3. Update state.json:
   - `phase_status`: `"completed"`
   - `updated_at`: current timestamp
   - Update the last entry in `phase_history`: set `completed_at` to current timestamp, `work_units_completed` to relevant count from metrics
4. Print progress line (see Section 8)
5. Execute transition logic (see Section 5)

**Step F: On postcondition FAIL**

- If this is the **first** failure for this phase:
  - Log `phase_retry` event to `phase-log.jsonl`:
    ```json
    {"event": "phase_retry", "phase": N, "phase_name": "{name}", "timestamp": "{ISO-8601}", "reason": "{which check failed}"}
    ```
  - Re-dispatch the agent (repeat Step C). Include context about which postcondition failed in the agent prompt, so the agent knows what to fix.
  - Repeat Steps D–F.
- If this is the **second** failure (retry also failed):
  - Update state.json:
    - `phase_status`: `"failed"`
    - `failure_reason`: description of which postcondition failed and why
    - `updated_at`: current timestamp
  - Log `phase_failed` event to `phase-log.jsonl`
  - Print error message:
    > "Phase {N} ({name}) failed after retry. Reason: {failure_reason}. The workspace is preserved at {WORKSPACE}. Use `/scholar:continue` to resume after manual inspection."
  - **Terminate.** Do not proceed to the next phase.

### 4.1 Agent Dispatch Prompts

Use these exact prompts when dispatching agents. Do not paraphrase — the runbooks are designed to be referenced by exact path.

**Phase 1 — Search:**
```
You are a search agent executing Phase 1 of a systematic literature review.

Read and follow the runbook at {PLUGIN_DIR}/runbooks/search.md exactly.

Workspace: {WORKSPACE}
Protocol: {WORKSPACE}/protocol.md

Execute all steps in the runbook. Write all output files to the workspace as specified. When complete, summarize what you did and what files you wrote.
```

**Phase 2 — Screening:**
```
You are a screening agent executing Phase 2 of a systematic literature review.

Read and follow the runbook at {PLUGIN_DIR}/runbooks/screen.md exactly.

Workspace: {WORKSPACE}
Protocol: {WORKSPACE}/protocol.md

Execute all steps in the runbook. Write all output files to the workspace as specified. When complete, summarize what you did and what files you wrote.
```

**Phase 3 — Snowballing:**
```
You are a snowballing agent executing Phase 3 of a systematic literature review.

Read and follow the runbook at {PLUGIN_DIR}/runbooks/snowball.md exactly.

Workspace: {WORKSPACE}
Protocol: {WORKSPACE}/protocol.md

Execute all steps in the runbook. Write all output files to the workspace as specified. When complete, summarize what you did and what files you wrote.
```

**Phase 3 (retry after feedback loop from Phase 4):**
```
You are a snowballing agent executing Phase 3 (feedback iteration {feedback_iterations}) of a systematic literature review.

Read and follow the runbook at {PLUGIN_DIR}/runbooks/snowball.md exactly.

Workspace: {WORKSPACE}
Protocol: {WORKSPACE}/protocol.md

This is a feedback iteration triggered by conceptual saturation in Phase 4. The newly included papers from the most recent Phase 4 run are the snowball seeds for this iteration. These papers are already in {WORKSPACE}/data/included.jsonl — focus snowballing on papers that do not yet have snowball-log entries.

Execute all steps in the runbook. Write all output files to the workspace as specified. When complete, summarize what you did and what files you wrote.
```

**Phase 4 — Extraction:**
```
You are an extraction agent executing Phase 4 of a systematic literature review.

Read and follow the runbook at {PLUGIN_DIR}/runbooks/extract.md exactly.

Workspace: {WORKSPACE}
Protocol: {WORKSPACE}/protocol.md

Execute all steps in the runbook. Write all output files to the workspace as specified. When complete, summarize what you did and what files you wrote.
```

**Phase 5 — Synthesis:**
```
You are a synthesis agent executing Phase 5 of a systematic literature review.

Read and follow the runbook at {PLUGIN_DIR}/runbooks/synthesize.md exactly.

Workspace: {WORKSPACE}
Protocol: {WORKSPACE}/protocol.md

Execute all steps in the runbook. Write all output files to the workspace as specified. When complete, summarize what you did and what files you wrote.
```

**On retry (any phase):** Append this to the dispatch prompt:
```
RETRY CONTEXT: This is a retry. The previous execution failed the following postcondition check: {which_check_failed}. Inspect the workspace files, identify what is missing or malformed, and complete or repair the output before terminating.
```

---

## Section 5: Transition Logic

After each phase passes its postconditions, apply the following transition rules before proceeding to the next phase. These rules are deterministic — evaluate them by reading workspace files.

### Phase 1 → Phase 2

Direct transition. No conditions. Update `state.json` to `current_phase: 2, phase_status: "pending"`.

### Phase 2 → Phase 3 (or diagnostic)

Read `{WORKSPACE}/data/included.jsonl`. Count the number of records.

- **If count > 0:** Direct transition to Phase 3. Update `state.json` to `current_phase: 3, phase_status: "pending"`.
- **If count = 0:** Diagnostic transition. Update `state.json`:
  - `current_phase`: 2
  - `phase_status`: `"needs_protocol_revision"`
  - `failure_reason`: `"No papers passed screening. Included corpus is empty."`
  - `updated_at`: current timestamp

  Log `phase_diagnostic` event to `phase-log.jsonl`.

  Print:
  > "No papers passed screening. The included corpus is empty. This typically means the search terms are too narrow, the inclusion criteria are too strict, or the date range excludes relevant work.
  >
  > To continue: review `{WORKSPACE}/logs/screening-log.jsonl` to understand why papers were excluded, then use `/scholar:continue` to re-enter Phase 0 and revise the protocol."

  **Terminate.** Do not proceed.

### Phase 3 → Phase 4

Direct transition. Update `state.json` to `current_phase: 4, phase_status: "pending"`.

### Phase 4 → Phase 3 (feedback loop) or Phase 5

After Phase 4 postconditions pass, compute conceptual saturation `Δ(n, k)`:

1. Read `{WORKSPACE}/data/concepts.jsonl`. Count total concepts → `total_concepts`.
2. Read `{WORKSPACE}/data/extractions.jsonl`. Get all extraction records sorted by timestamp. Identify the last `k` papers extracted (use the `k` value from `protocol.md`).
3. From `concepts.jsonl`, count concepts whose `first_seen_in` field is one of those last `k` paper IDs → `new_concepts_in_last_k`.
4. Compute `Δ(n, k) = new_concepts_in_last_k / total_concepts`. If `total_concepts = 0`, set `Δ(n, k) = 0`.
5. Read `feedback_iterations` from `state.json`. Read `max_feedback_iterations` from `protocol.md`.

**Decision:**

- If `Δ(n, k) ≥ θ_c` AND `feedback_iterations < max_feedback_iterations`:
  - Increment `feedback_iterations` in `state.json`
  - Log `saturation_check` to `phase-log.jsonl`:
    ```json
    {"event": "saturation_check", "phase": 4, "type": "conceptual", "timestamp": "{ISO-8601}", "saturation_metric": "{Δ}", "threshold": "{θ_c}", "decision": "feedback_loop", "feedback_iteration": N}
    ```
  - Update `state.json` to `current_phase: 3, phase_status: "pending"`
  - Print:
    > "Conceptual saturation Δ(n,k) = {Δ:.3f} ≥ θ_c = {θ_c}. Concept space still expanding. Initiating feedback loop (iteration {N} of {max}). Returning to Phase 3."
  - Proceed to Phase 3 using the feedback-loop dispatch prompt.

- If `Δ(n, k) < θ_c` OR `feedback_iterations ≥ max_feedback_iterations`:
  - Log `saturation_check` to `phase-log.jsonl`:
    ```json
    {"event": "saturation_check", "phase": 4, "type": "conceptual", "timestamp": "{ISO-8601}", "saturation_metric": "{Δ}", "threshold": "{θ_c}", "decision": "proceed_to_synthesis"}
    ```
  - Update `state.json` to `current_phase: 5, phase_status: "pending"`
  - Update `state.json` metrics: `conceptual_saturation: Δ`
  - Proceed to Phase 5.

### Phase 5 → Done

After Phase 5 postconditions pass:
1. Update `state.json`:
   - `current_phase`: 5
   - `phase_status`: `"completed"`
   - `updated_at`: current timestamp
2. Print the full completion summary (see Section 8).

---

## Section 6: Postcondition Check Procedure

After each phase agent returns, run the postcondition checks defined in `{PLUGIN_DIR}/runbooks/postconditions.md`. The checks are deterministic — read files, verify structural conditions. No inference.

### How to Run Checks

For each check defined in `postconditions.md` for the current phase:

1. Read the specified file(s) using the Read or Bash tool
2. Evaluate the condition as stated
3. If the condition holds: mark the check as passed
4. If the condition does not hold: record which check failed, what the expected condition was, and what was actually found

If **all** checks pass: proceed to Step E of the execution loop (metrics update and transition).

If **any** check fails: proceed to Step F (retry logic).

### Phase-specific Check Summary

The complete check specifications are in `{PLUGIN_DIR}/runbooks/postconditions.md`. Summary of what is checked per phase:

- **Phase 1:** All queries from protocol were executed; candidates.jsonl non-empty; no duplicate IDs; every record has id, title, abstract, authors, year.
- **Phase 2:** All candidates have a final screening decision; every paper in included.jsonl has a corresponding include decision in screening-log.jsonl; no orphan inclusions.
- **Phase 3:** Termination condition met (saturation or max depth); all seed papers have forward and backward snowball entries; truncations logged; new inclusions in candidates.jsonl and included.jsonl.
- **Phase 4:** All included papers have extraction records; concepts.jsonl non-empty; concept-matrix.md exists; all referenced concept IDs are defined; saturation check event logged.
- **Phase 5:** All included papers cited in review.md; all sub-questions addressed in question-answers.jsonl; bibliography count matches citation count in review.md; all required section headers present.

---

## Section 7: Metrics Update

After each phase passes postconditions, update `metrics` in `{WORKSPACE}/state.json` by reading the workspace files. All counts are exact — count file lines or records, do not estimate.

### Metric Computation

**`total_candidates`:** Count the number of lines in `{WORKSPACE}/data/candidates.jsonl`. Each line is one candidate record. Use:
```bash
wc -l < {WORKSPACE}/data/candidates.jsonl
```
(Handle the case where the file does not exist: count = 0.)

**`total_included`:** Count lines in `{WORKSPACE}/data/included.jsonl`.

**`total_excluded`:** Count entries in `{WORKSPACE}/logs/screening-log.jsonl` where `decision == "exclude"`. Read the file and filter.

**`total_flagged`:** Count entries in `{WORKSPACE}/logs/screening-log.jsonl` where `decision == "flag_for_full_text"`.

**`snowball_depth_reached`:** Read `{WORKSPACE}/logs/snowball-log.jsonl`. Find the maximum value of `depth_level` across all entries. If the file does not exist, set to 0.

**`discovery_saturation`:** Read the most recent `saturation_check` event with `type == "discovery"` from `{WORKSPACE}/logs/phase-log.jsonl`. Extract `saturation_metric`. If no such event, set to `null`.

**`conceptual_saturation`:** Read the most recent `saturation_check` event with `type == "conceptual"` from `{WORKSPACE}/logs/phase-log.jsonl`. Extract `saturation_metric`. If no such event, set to `null`.

**`concepts_count`:** Count lines in `{WORKSPACE}/data/concepts.jsonl`. If the file does not exist, set to 0.

**`extraction_complete_count`:** Count the number of unique `paper_id` values in `{WORKSPACE}/data/extractions.jsonl`. If the file does not exist, set to 0.

After computing all metrics, write the updated `state.json`. Also update `updated_at` to the current ISO-8601 timestamp.

---

## Section 8: Progress Reporting

### Phase Completion Lines

After each phase transition prints one progress line using this format:

- **Phase 1 complete:**
  > "✓ Phase 1 (Search) complete — {total_candidates} candidates found"

- **Phase 2 complete:**
  > "✓ Phase 2 (Screening) complete — {total_included} included, {total_excluded} excluded ({total_flagged} flagged during screening)"

- **Phase 3 complete:**
  > "✓ Phase 3 (Snowballing) complete — {papers_added} papers added via snowballing, depth {snowball_depth_reached}"

  Where `papers_added = total_included_after - total_included_before`. Store `total_included_before` at Phase 3 start.

- **Phase 4 complete:**
  > "✓ Phase 4 (Extraction) complete — {extraction_complete_count} papers extracted, {concepts_count} concepts identified"

  If this triggers a feedback loop, also print:
  > "  → Δ(n,k) = {value:.3f} ≥ θ_c = {θ_c} — returning to Phase 3 for feedback iteration {N}"

- **Phase 5 complete:**
  > "✓ Phase 5 (Synthesis) complete — review ready"

### Completion Summary

After Phase 5, print the full statistics summary:

```
═══════════════════════════════════════════════
  Scholar — Review Complete
═══════════════════════════════════════════════
  Project:     {project_slug}
  Question:    {research_question}
  Completed:   {ISO-8601 date}

  Corpus
  ──────────────────────────────────────────
  Candidates:           {total_candidates}
  Included:             {total_included}
  Excluded:             {total_excluded}
  Flagged (screened):   {total_flagged}

  Discovery
  ──────────────────────────────────────────
  Snowball depth:       {snowball_depth_reached}
  Discovery saturation: {discovery_saturation or "N/A"}

  Extraction
  ──────────────────────────────────────────
  Papers extracted:     {extraction_complete_count}
  Concepts identified:  {concepts_count}
  Conceptual sat.:      {conceptual_saturation or "N/A"}
  Feedback iterations:  {feedback_iterations}

  Outputs
  ──────────────────────────────────────────
  Review:        {WORKSPACE}/review.md
  Bibliography:  {WORKSPACE}/references.bib
  Protocol:      {WORKSPACE}/protocol.md
  State:         {WORKSPACE}/state.json
═══════════════════════════════════════════════
```

---

## Section 9: Error Handling

### Rate Limit Errors (HTTP 429)

Phase agents handle rate limit errors internally using exponential backoff. If a rate limit error propagates back to you (the orchestrator), wait 30 seconds and re-dispatch the agent. The agents are designed to resume from partial work — they write as they go and check what has already been completed at the start of each batch.

### Agent Failure (agent returns without completing work)

Check postconditions. If any postcondition fails, follow the retry logic in Section 4 Step F. The postcondition check tells you whether partial work was done. Include the failed postcondition context in the retry dispatch prompt so the agent knows what to fix.

### MCP Server Unavailable

At the start of Phase 1, before dispatching the search agent, verify that both Semantic Scholar and arXiv MCP tools are accessible. Do a simple test call (e.g., `mcp__semantic-scholar__search_paper` with a trivial query, `mcp__arxiv__list_papers`).

- If **both** servers are unavailable: report to the user and terminate. The search phase cannot proceed without at least one discovery source.
- If **one** server is unavailable: warn the user:
  > "Warning: {server} MCP is unavailable. The review will proceed using {other_server} only. Coverage may be reduced."
  Continue with the available server. Record this in `phase-log.jsonl` as a `degraded_operation` event.

### Workspace Corruption

If `state.json` is unreadable or contains invalid JSON:
- Report: "Cannot read {WORKSPACE}/state.json. The workspace may be corrupted. Inspect the file manually and correct the JSON, then use `/scholar:continue` to resume."
- Do not attempt to repair state.json automatically.
- Terminate.

If individual data files are missing or truncated mid-phase:
- The retry logic handles this. Run postcondition checks to identify what is missing, then re-dispatch the agent with context.

### Runbook Not Found

If a runbook file does not exist at the expected path (e.g., `{PLUGIN_DIR}/runbooks/search.md`):
- Report: "Runbook {runbook_path} not found. The plugin installation may be incomplete. Reinstall the Scholar plugin and try again."
- Terminate.

### Unexpected Phase State

If `state.json` contains a `phase_status` that is not one of `{pending, in_progress, complete, failed, needs_protocol_revision}`, or if `current_phase` is outside the range 0–5:
- Report the exact values found and instruct the user to inspect the file.
- Terminate without making changes.

---

## Section 10: Resuming an Existing Review

If this skill is invoked and `state.json` already exists in a workspace matching the project slug:
- Read `state.json`
- If `protocol_approved` is `false`: offer to resume Phase 0
- If `protocol_approved` is `true` and `phase_status` is not `"completed"`: offer to resume from `current_phase`
- If `phase_status` is `"completed"` (Phase 5 done): report that the review is already complete and show the workspace path

Prompt the user:
> "Found existing workspace at {WORKSPACE} (Phase {current_phase}, status: {phase_status}). Resume? [y/n]"

On 'y': proceed from the current phase.
On 'n': offer to create a new project slug (e.g., append `-2`) or let the user choose a different name.

---

## Execution Checklist

Before starting, confirm you have:
- [ ] Research question (from argument or user input)
- [ ] Project slug generated
- [ ] Workspace created at `~/research/{slug}/`
- [ ] `state.json` initialized
- [ ] `PLUGIN_DIR` resolved (the directory containing `plugin.json`)
- [ ] `WORKSPACE` variable set to `~/research/{slug}/`

Before each phase dispatch, confirm:
- [ ] `state.json` updated to `phase_status: "in_progress"`
- [ ] `phase_start` event logged to `phase-log.jsonl`
- [ ] Agent prompt includes exact `PLUGIN_DIR` and `WORKSPACE` paths (not template placeholders)

After each phase, confirm:
- [ ] All postconditions checked (reference `{PLUGIN_DIR}/runbooks/postconditions.md`)
- [ ] Metrics updated in `state.json`
- [ ] `phase_complete` event logged
- [ ] Progress line printed
- [ ] Transition logic evaluated and next phase determined
