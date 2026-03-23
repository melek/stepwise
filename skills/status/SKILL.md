---
name: status
description: Report the current status of a literature review project.
argument-hint: "[project-slug]"
allowed-tools: Read, Glob, Grep
---

# Status Skill — Project Reporting

## Purpose
Read-only reporting on literature review projects. No modifications to any files.

## Process

### 1. Locate Project
- If argument provided: look for workspace at `~/research/{argument}/`
- If no argument: list all directories in `~/research/`, show summary for each

### 2. Project Summary (when listing all)
For each project directory in `~/research/`:
- Read `state.json`
- Print one line: `{slug} — Phase {N} ({phase_name}) — {phase_status} — {total_included} papers included`

Phase names: 0=Protocol, 1=Search, 2=Screening, 3=Snowballing, 4=Extraction, 5=Synthesis

### 3. Detailed Report (single project)
Read `state.json`, `protocol.md`, and log files. Print:

```
Project: {project_slug}
Question: {research_question}
Created: {created_at}
Updated: {updated_at}

Current Phase: {current_phase} — {phase_name}
Phase Status: {phase_status}
{If failed: "Failure Reason: {failure_reason}"}

Metrics:
  Candidates:  {total_candidates}
  Included:    {total_included}
  Excluded:    {total_excluded}
  Flagged:     {total_flagged}
  Snowball Depth: {snowball_depth_reached}
  Concepts:    {concepts_count}
  Extractions: {extraction_complete_count}
  Discovery Saturation:   {discovery_saturation or "—"}
  Conceptual Saturation:  {conceptual_saturation or "—"}

Phase History:
  {For each entry in phase_history: "Phase {phase}: {started_at} → {completed_at or 'in progress'}"}

Next Action: {describe what /stepwise:continue would do}
```

### 4. Completed Project Report
If current_phase = 5 and phase_status = completed:
- Additionally report: location of review.md, word count, number of references in references.bib
- Print: "Review complete. Output: {workspace}/review.md"

### 5. Error Handling
- If workspace not found: "No project found at ~/research/{slug}/. Use /stepwise:research to start a new review."
- If state.json missing or corrupt: "Workspace exists but state.json is missing or unreadable. Manual inspection needed."
- If ~/research/ doesn't exist: "No research projects found. Use /stepwise:research to start your first review."
