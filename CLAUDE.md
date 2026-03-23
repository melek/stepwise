# CLAUDE.md — Stepwise

Autonomous systematic literature review plugin for Claude Code. Implements Kitchenham SLR protocol with Wohlin snowballing, verified inference quarantine, and PRISMA 2020 compliance.

## Commands

```bash
# Run tests (85 tests, pytest)
cd stepwise && .venv/bin/python3 -m pytest tests/ -v

# CLI subcommands (all output JSON to stdout)
python3 -m lib.cli metrics --workspace ~/research/my-project/
python3 -m lib.cli postcondition --phase 2 --workspace ~/research/my-project/
python3 -m lib.cli transition --action next --workspace ~/research/my-project/
python3 -m lib.cli saturation --type conceptual --k 5 --workspace ~/research/my-project/
python3 -m lib.cli preprocess --type screening --workspace ~/research/my-project/
python3 -m lib.cli prisma --type prisma2020 --workspace ~/research/my-project/
python3 -m lib.cli export --format ris --dataset included --workspace ~/research/my-project/
python3 -m lib.cli validate-inference --contract SCREEN_CRITERION --record '{...}'
python3 -m lib.cli parse-sections --file papers/paper.txt
```

## Architecture

### Pipeline

6-phase pipeline orchestrated by `skills/research/SKILL.md`:

```
Phase 0: Protocol Definition     [interactive — user + orchestrator]
Phase 1: Search                  [autonomous — search agent + runbook]
Phase 2: Screening               [autonomous — screen agent + runbook]
Phase 3: Snowballing             [autonomous — snowball agent + runbook]
Phase 4: Data Extraction         [autonomous — extract agent + runbook]
Phase 5: Synthesis               [autonomous — synthesize agent + runbook]
```

Between phases, the orchestrator runs preprocessing (evidence windows for screening, themed briefs for synthesis) and postcondition checks. All state resides in the filesystem workspace (`~/research/{slug}/`).

### lib/ Modules

All pure functions with no I/O (except `cli.py` which is the thin I/O shell).

| Module | Purpose | Verified? |
|--------|---------|-----------|
| `state.py` | Phase state machine (6 phases, 5 statuses) | Dafny companion: `spec/state.dfy` |
| `saturation.py` | Discovery and conceptual saturation (exact Fraction arithmetic) | Dafny companion: `spec/saturation.dfy` |
| `postconditions.py` | Per-phase structural checks + per-record validators | Tested (85 tests) |
| `oracle_contracts.py` | Named contracts wrapping validators with recovery and provenance | Tested |
| `preprocess.py` | Deterministic preprocessing (screening evidence windows, synthesis concept clustering) | Tested |
| `prisma.py` | PRISMA 2020 (27 items) + PRISMA-trAIce (7 items) compliance checking | Tested |
| `export.py` | PRISMA Mermaid flow diagram, RIS/CSV export | Tested |
| `metrics.py` | Workspace metric recomputation | Tested |
| `section_parser.py` | Markdown section extraction for field-guided extraction | Tested |
| `cli.py` | Argparse CLI delegating to pure functions | I/O boundary |

### Oracle Contracts

Every inference call in Phases 2-5 is validated against a named contract before output is written:

| Contract | Phase | Validates |
|----------|-------|-----------|
| `SCREEN_CRITERION` | 2, 3 | Single criterion evaluation (met, evidence, source, criterion_id, criterion_type) |
| `SCREEN_DECISION` | 2, 3 | Complete screening decision (biconditional rules: include iff all IC met and no EC met) |
| `EXTRACT_FIELD` | 4 | Single extraction field (confidence ceiling for abstract-only) |
| `IDENTIFY_CONCEPTS` | 4 | Concept record (slug pattern, definition length, frequency) |
| `SYNTHESIZE_CLAIM` | 5 | Citation integrity (every paragraph cited, no phantom refs, data completeness qualification) |

Failed validation triggers documented recovery (e.g., `met=unclear` for criterion failures, `extraction_failed` for field failures). Every record gets `_validated_by` provenance metadata.

### Data Sources (MCP)

| MCP Server | Required | Purpose |
|------------|----------|---------|
| Semantic Scholar | Yes | Paper search, metadata, citation graph |
| arXiv | Yes | Paper search, PDF download |
| PubMed | No | Biomedical literature (PRISMA database coverage) |
| Unpaywall | No | Open-access full text for DOI papers |
| Scite | No | Smart Citations (supporting/contrasting/mentioning) |
| paper-search-mcp | No | 20+ databases (IEEE, ACM, DBLP, OpenAlex, etc.) |
| Zotero | No | Reference management export |

### Output Formats

Configurable via `output_format` in the protocol:

| Format | Template | PRISMA Checklist | Appendices |
|--------|----------|-----------------|------------|
| `prisma_2020` (default) | `review-template-prisma.md` | Yes (27 items + trAIce) | A (papers), B (concepts), C (PRISMA), D (trAIce) |
| `kitchenham` | `review-template-kitchenham.md` | No | A (papers), B (concepts) |
| `narrative` | `review-template-narrative.md` | No | None |

## Axioms

1. **A1 — Deterministic structure, nondeterministic content.** Process decisions are deterministic. Content decisions use inference behind validation gates.
2. **A2 — Workspace is complete state.** No implicit state.
3. **A3 — Append-only evidence.** Records are never modified or deleted.
4. **A4 — Bounded work per phase.** Enforced by counters, not judgment.
5. **A5 — Saturation is measured.** Discovery and conceptual saturation use exact rational arithmetic.
6. **A6 — Sovereignty.** All data local. Cloud APIs for discovery only.
7. **A7 — Reproducibility.** Enough state recorded to understand why results differ between runs.

## Governance

Design changes follow the change management protocol in `docs/methodology/CHANGE_PROTOCOL.md` with expert panel review per `docs/methodology/EXPERT_ROSTER.md`.

## Key References

- Kitchenham & Charters (2007) — Systematic Literature Review methodology
- Wohlin (2014) — Snowballing procedure
- Page et al. (2021) — PRISMA 2020 reporting guidelines
- Thomas & Harden (2008) — Thematic synthesis
- PRISMA-trAIce (JMIR AI 2025) — AI transparency in systematic reviews
