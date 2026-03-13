---
name: continue
description: Resume an existing systematic literature review from where it left off.
argument-hint: "[project-slug]"
allowed-tools: Read, Write, Edit, Bash, Glob, Grep, Agent, ToolSearch, mcp__semantic-scholar__search_paper, mcp__semantic-scholar__get_paper, mcp__semantic-scholar__get_citation, mcp__semantic-scholar__get_authors, mcp__arxiv__search_papers, mcp__arxiv__download_paper, mcp__arxiv__read_paper, mcp__arxiv__list_papers, mcp__unpaywall__unpaywall_search_titles, mcp__unpaywall__unpaywall_get_by_doi, mcp__unpaywall__unpaywall_get_fulltext_links, mcp__unpaywall__unpaywall_fetch_pdf_text, mcp__zotero__zotero_search, mcp__zotero__zotero_get_item, mcp__zotero__zotero_list_collections, mcp__zotero__zotero_get_collection_items
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
| 1-5 | completed | Advance to next phase. Update state.json: current_phase += 1, phase_status = pending. Enter orchestration loop. |
| 1-5 | in_progress | Phase was interrupted mid-execution. Re-run current phase from scratch (agents are stateless, but postconditions will detect partial work). Enter orchestration loop. |
| 1-5 | failed | Report failure reason from state.json. Ask user: retry this phase, or revise protocol? If retry: reset phase_status to pending, enter orchestration loop. If revise: set current_phase = 0, phase_status = in_progress. |
| 1-5 | pending | Phase ready to start. Enter orchestration loop. |
| any | needs_protocol_revision | Phase 2 screening found no papers. Report the issue. Re-enter Phase 0 interactively to revise search terms or criteria. On new approval: reset to Phase 1, clear stale data files. |
| 5 | completed (final) | Review is complete. Report final statistics and location of review.md. |

### 4. Orchestration Loop
The orchestration loop is identical to the one in the research skill. For the current phase:
1. Set phase_status = "in_progress" in state.json
2. Log phase_start to logs/phase-log.jsonl
3. Dispatch the appropriate agent using the Agent tool:
   - Phase 1: runbooks/search.md
   - Phase 2: runbooks/screen.md
   - Phase 3: runbooks/snowball.md
   - Phase 4: runbooks/extract.md
   - Phase 5: runbooks/synthesize.md
4. Agent dispatch prompt format:
   "You are a {phase_name} agent. Read and follow the runbook at {plugin_dir}/runbooks/{runbook}.md exactly. Workspace: {workspace_path}. Protocol: {workspace_path}/protocol.md"
5. On completion: run postcondition checks per runbooks/postconditions.md
6. On pass: update metrics, log transition, advance phase
7. On fail: retry once, then record failure and terminate
8. Handle Phase 4→3 feedback loop (check conceptual saturation)
9. Continue until Phase 5 completes or failure

### 5. Progress Reporting
Same format as research skill:
- Per phase: "✓ Phase {N} ({name}) complete — {metric}"
- On completion: full statistics summary

### 6. Stale Data Handling
When re-entering Phase 0 after needs_protocol_revision:
- Archive current data/ and logs/ to data_archive_{timestamp}/ and logs_archive_{timestamp}/
- Create fresh data/ and logs/ directories
- This preserves the evidence trail (A3) while allowing a clean restart
