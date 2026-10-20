---
name: continue
description: Resume an existing systematic literature review from where it left off.
argument-hint: "[project-slug]"
allowed-tools: Read, Write, Edit, Bash, Glob, Grep, Agent, ToolSearch, mcp__semantic-scholar__search_paper, mcp__semantic-scholar__get_paper, mcp__semantic-scholar__get_citation, mcp__semantic-scholar__get_authors, mcp__arxiv__search_papers, mcp__arxiv__download_paper, mcp__arxiv__read_paper, mcp__arxiv__list_papers, mcp__unpaywall__unpaywall_search_titles, mcp__unpaywall__unpaywall_get_by_doi, mcp__unpaywall__unpaywall_get_fulltext_links, mcp__unpaywall__unpaywall_fetch_pdf_text, mcp__zotero__zotero_search, mcp__zotero__zotero_get_item, mcp__zotero__zotero_list_collections, mcp__zotero__zotero_get_collection_items, mcp__pubmed__search, mcp__pubmed__get_article, mcp__pubmed__get_related, mcp__scite__search_citations, mcp__scite__get_paper_citations, mcp__paper_search__search_papers, mcp__paper_search__download_with_fallback
---

# Continue Skill — Resume Literature Review

## Purpose
Resume an existing systematic literature review from its last recorded state. The workspace is the complete state (Axiom A2) — read state.json to determine exactly where to pick up.

## Process

### 1. Locate Project
- If argument provided: look for workspace at `~/research/{argument}/`
- If no argument: list all directories in `~/research/`, show each project's status (read state.json from each), ask user to select

### 2. Read State
- Read `{workspace}/state.json`
- Read `{workspace}/protocol.md`
- Determine current situation from `current_phase` and `phase_status`

### 3. Determine Next Action

| current_phase | phase_status | Action |
|---------------|-------------|--------|
| 0 | in_progress | Protocol definition incomplete. Re-enter Phase 0: read protocol.md (may be partial), continue filling fields interactively with user, get approval. |
| 1-5 | pending, in_progress or completed | Enter the orchestration loop. `step` decides: it starts a pending phase, checks an interrupted `in_progress` phase (completing it if its work is done, retrying it if not), and advances a completed one. |
| 1-5 | failed | `RECOVERY:` stop. Report the failure reason from state.json with evidence and your recommendation, then ask: retry this phase, or revise protocol? If retry: run `step --reset` (below), then continue the loop. If revise: set current_phase = 0, phase_status = in_progress. |
| any | needs_protocol_revision | Phase 2 screening found no papers. Report the issue. Re-enter Phase 0 interactively to revise search terms or criteria. On new approval: reset to Phase 1, clear stale data files. Also set `retry_count` and `feedback_iterations` to 0 so the fresh run gets its own retry and feedback budget. |
| 5 | completed (final) | Review is complete. Report final statistics and location of review.md. |

### 4. Orchestration Loop
Identical to the research skill's (Section 4, "The Execution Loop"): run

```bash
python3 {PLUGIN_DIR}/lib/cli.py step --workspace {WORKSPACE}
```

and do what it returns (`dispatch` an agent with the Section 4.1 prompt, `stop`, or `done`), calling `step` again each time an agent returns. To retry a failed phase after a recovery, run `step --reset` instead of the plain call. Never edit `state.json` or `phase-log.jsonl` by hand during Phases 1–5.

### Stop Policy
Same as the research skill (Section 1, "Stop Policy"): after resuming, the only stops are `DECISION REQUIRED:` and `RECOVERY:`. Don't ask before advancing a phase whose postconditions passed.

### 5. Progress Reporting
Same format as research skill:
- Per phase: "✓ Phase {N} ({name}) complete — {metric}"
- On completion: full statistics summary

### 6. Stale Data Handling
When re-entering Phase 0 after needs_protocol_revision:
- Archive current data/ and logs/ to data_archive_{timestamp}/ and logs_archive_{timestamp}/
- Create fresh data/ and logs/ directories
- This preserves the evidence trail (A3) while allowing a clean restart
