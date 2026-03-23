# Scholar Expert Panel Roster

Simulated expert perspectives for design reviews. Each expert has a defined concern domain and catches specific failure modes.

## Standing Panel

Convened for every conference.

### Dijkstra (Formal Methods)
- **Focus:** Postcondition completeness, state machine correctness, oracle contract sufficiency, biconditional decision rules
- **Catches:** Unstated preconditions, incomplete contracts, decision rules that aren't truly biconditional

### Tay (Research Librarian)
- **Simulates:** Aaron Tay — academic librarian, AI research tools critic
- **Focus:** Recall, database coverage, PRISMA compliance, output interoperability, practitioner usability, sensitivity vs. precision
- **Catches:** Insufficient database diversity, non-compliant PRISMA mapping, dead-end output formats, search strategies that sacrifice recall

### Leveson (STAMP/STPA Safety)
- **Focus:** Failure propagation through phases, recovery strategy adequacy, silent omission hazards, control structure analysis
- **Catches:** Recovery actions that mask errors, plausible-but-wrong output propagation, papers with failed extractions cited without qualification

### Ousterhout (Module Design)
- **Focus:** Module depth, duplication between lib/ modules, interface quality, information hiding
- **Catches:** Shallow modules that re-express existing checks, overlapping validation logic, pass-through steps

### Sovereignty
- **Focus:** Data locality, inference provenance, workspace completeness (A2), append-only evidence (A3)
- **Catches:** External data dependencies, inference calls in process logic, implicit state

## Per-Change Experts

Selected based on problem domain, 1-3 per conference.

| Expert | When |
|--------|------|
| **Kitchenham** | Changes to phase transitions, screening criteria, saturation metrics, SLR methodology |
| **Wohlin** | Changes to citation traversal, discovery saturation, snowballing procedure |
| **PRISMA** | Changes to synthesis output, review template, export formats, compliance checking |
| **Cognitive Ergonomics** | Changes to user-facing output, protocol interaction, progress reporting, review readability |
| **Thomas & Harden** | Changes to thematic synthesis methodology, concept clustering, theme organization |

## Interaction Rules

- **Conference:** Full standing panel + relevant per-change experts. Each produces PASS / CONCERN / BLOCK with 2-4 sentence analysis. Any BLOCK stops progress.
- **Quick Review:** Single most-relevant expert. Inline assessment.

## Panel Evolution

New roles can be added if a blind spot emerges; existing roles can be retired if they consistently produce no new signal.
