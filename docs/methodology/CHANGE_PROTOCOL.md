# Scholar Change Management Protocol

Every change begins with scope classification. No code is written until the protocol for that scope tier is satisfied.

## Phase 0 — Scope Classification

| Tier | Scope | Examples | Required Phases |
|------|-------|----------|-----------------|
| **Tier 1 (Patch)** | No behavioral change | Test fixes, doc edits, template tweaks | State what + why, implement |
| **Tier 2 (Feature)** | New/modified observable behavior | New MCP integration, new postcondition, new output format, new oracle contract | Phases 1-4 (full protocol) |
| **Tier 3 (Architectural)** | Pipeline structure, schema changes | New review phase, state machine modification, oracle contract schema change | Phases 1-4 with extended review |

If uncertain, classify upward.

## Phase 1 — Specification Review (Tier 2+)

1. Identify governing spec sections — quote the relevant parts of the design spec
2. Read every file that will be modified
3. State the change in spec terms — prescribed behavior, current behavior, gap
4. Identify semantic contracts — what must be true beyond structural correctness

## Phase 2 — Expert Panel Review (Tier 2+)

Reviews the Phase 1 analysis. Each panelist produces PASS / CONCERN / BLOCK with 2-4 sentence analysis.

See `EXPERT_ROSTER.md` for the standing panel and per-change experts.

Any BLOCK stops progress until the Phase 1 analysis is revised.

## Phase 3 — Implementation Plan (Tier 2+)

1. Files to create/modify with specific changes per file
2. Test plan — one test minimum per semantic contract from Phase 1
3. Axiom compliance checklist — one sentence per applicable axiom
4. Rollback boundary — safe state if interrupted

User approves, modifies, or rejects this plan.

## Phase 4 — Implementation

- Execute in plan order
- Run tests after each logical unit
- If implementation reveals a gap in Phase 1 analysis: STOP. Return to Phase 1.
- Commit messages reference semantic contracts

## Quick-Fix Prohibition

No quick-fix path exists. Bug found after implementation -> classify via Phase 0. If the fix reveals a missed semantic contract, that's Tier 2.
