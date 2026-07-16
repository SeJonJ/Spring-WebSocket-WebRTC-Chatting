# PDCA Workflow and Phase Document Templates

Use this when a task requires Phase 00–06 planning, an optional prior-knowledge
scan, an independent/cross-model review, or a phase document template. The phase
set and per-level obligation are configured in `profile.pdca`; this document
defines the neutral methodology. Domain specifics (stacks, high-risk domains,
component names) come from the profile, never from this file.

---

## Workflow Overview

| Phase | Name | Key Tasks | Deliverable |
|:---:|:---|:---|:---|
| 00 | Base Plan | Strategy, impact analysis, prior knowledge, technical risk | `plan_docs/00-base_plan/.../[feature]_plan.md` |
| 01 | Plan | Requirements, data model, API specifications, acceptance matrix | `plan_docs/01-plan/[feature].md` |
| 02 | Design | Class/interface design, sequence diagrams, error codes | `plan_docs/02-design/[feature].md` |
| 03 | Implementation | Pre-code ownership/checklist skeleton, implementation, unit testing, verification evidence | `plan_docs/03-implementation/[feature].md` |
| 04 | Analyze | Design vs implementation gap analysis by **leader** + **qa** (coverage + acceptance evidence). No single verdict here. | `plan_docs/04-analyze/[feature].md` |
| 05 | Expert Review | Independent synthesis by **reviewer** (+ cross-model reviewer when enabled). Acceptance unresolved items block APPROVED. Final APPROVED/FAIL/BLOCKED issued here. | `plan_docs/05-expert-review/[feature].md` |
| 06 | Report | Final completion report by **leader**. **Written only after Phase 05 = APPROVED.** If 05 = FAIL/BLOCKED → rework → re-review → APPROVED → then 06. | `plan_docs/06-report/[feature].md` |

Roles (`leader` / `reviewer` / `qa`) are the neutral CORE roster — map to your
team in `profile.team`.

## Phase Separation Rules

### Mandatory Writing Rule
- Each phase's writing obligation follows the risk level in
  `AGENT_GUIDE.md` Risk & Workflow Gate and `profile.pdca`.
- An empty `plan_docs/{phase}/` directory is **not** a convention. Treat it as a
  prior task's omission, not a precedent for skipping.
- Skipping a mandatory phase requires an explicit reason in the plan body and
  user approval.
- The `pre-implementation-gate` hook **blocks** L2/L3 implementation when a
  required pre-implementation phase is missing, and blocks Phase 06 until the
  approve phase records `APPROVED`.

### 00 vs 01 — the most commonly confused boundary
| Dimension | 00 Base Plan | 01 Plan |
|:---|:---|:---|
| Nature | **CONTEXT** — why / what / impact | **CONTENT** — details of this feature |
| Covers | Strategy, prior knowledge, component impact, before/after, technical risk | User stories, data schema/DTO, API spec, detailed design |
| Does NOT cover | Function signatures, API schemas, file/line numbers | Strategic judgment, impact analysis, prior-knowledge scan |
| Length | 1–2 page context | Proportional to feature scope |

### Other boundaries
- **02 Design vs 03 Implementation**: 02 = architecture / sequence / error codes / interface design; 03 = file ownership / implementation checklist / acceptance trace / build & test results. 03 is opened before source edits with ownership and checklist, then completed after code with evidence.
- **04 Analyze vs 05 Expert Review**: 04 = leader (responsible) + qa (coverage) — gap (match rate) + missing items + coverage. **No standalone verdict.** 05 = reviewer (+ cross-model when enabled) — independent synthesis + cross-check; final verdict (APPROVED/FAIL/BLOCKED) issued here. Cross-model review is recorded in **05, not 04**.

### Signals of incorrect separation
- 00 contains a function signature → move to 01
- 00 contains a file/line number → move to 01 or 02
- 01 contains prior-knowledge scan → move to 00
- 02 contains build/test results → move to 03

## Component-level Plan Docs

A project may run **two parallel plan_docs trees** (configured via
`profile.paths.component_plan_docs` and `profile.components`):

| Tree | Path | Purpose | Owner |
|:---|:---|:---|:---|
| Root (feature-wide PDCA) | `plan_docs/00–06/[feature].md` | Cross-component, project-wide design under standard templates | leader |
| Component-level | `{component}/plan_docs/[feature]_plan.md` | Code-level implementation design within one component boundary | component owner |

### Writing order for L2/L3 changes
1. Root `00-base_plan/` — strategy + impact
2. Root `01-plan/` — feature requirements + data schema + API (cross-component contract)
3. Root `02-design/` — architecture + sequence + error codes
4. Component `{component}/plan_docs/` — code-level design (free format)
5. Root `03-implementation/` — pre-code ownership/checklist skeleton + acceptance trace
6. Implementation + tests
7. Update root `03-implementation/` — files changed, checklist results, build/test evidence
8. Root `04-analyze/`, `05-expert-review/`, `06-report/` — gap + acceptance evidence + review + report

### Conventions
- Root tree is the **single source of truth for the cross-component contract** (DTO fields, event names, error codes).
- File-naming stem must match across root and component trees for the same feature.
- Component tree owns code-level decisions inside its boundary; cross-component impact must be reflected back into root `01-plan`/`02-design`.

## Prior-Knowledge Scan (optional — knowledge_capture)

When `profile.knowledge_capture.vault_path` is set and the knowledge provider is
available, scan prior knowledge before writing the base plan; otherwise record
N/A. Summarize findings under `## 0. Prior Knowledge` in the base plan.

```markdown
## 0. Prior Knowledge
Status: N/A
Reason: [knowledge_capture disabled / provider unavailable]
Decision: Proceeding from repository files only.
```

## Independent / Cross-model Review Protocol

Independent review is **mandatory for L3** (recommended for L2). It is recorded in
**Phase 05**, not 04. The reviewer runtime is resolved by `sage doctor`
(same-runtime clean-context, or opposite-runtime when `profile.options.cross_model`
is on and reachable — `docs/agent/review-protocol.md`).

1. If `plan_docs/04-analyze/[feature].md` exists, read the lead's gap findings + coverage first; build on them.
2. Review from an independent perspective: design intent vs implementation, stack fitness, lifecycle/edge-case/security/test/UX risk.
3. **High-risk architecture gate**: before a review-rework loop, check whether findings change a high-risk domain declared in `profile.risk` (L3). If a new architecture change is detected, stop automatic rework and get user approval. Local fixes inside the approved design are not blocked.
4. **Cross-model invocation** (when enabled): run `sage cross-check --packet-file <packet>`, which calls the peer runtime directly (claude-host → `codex exec`, codex-host → `claude -p`) at `cross_model.effort` (default `high`). The packet carries all phase documents + implementation files. Request context-based external review (not a plain diff review) and a final recommendation: APPROVED / FAIL / BLOCKED.
5. **Acceptance gate**: read the Phase 01 acceptance matrix and Phase 04 evidence table. Required items with `FAIL` or `NOT TESTED` block `APPROVED`; use `N/A` only with an explicit out-of-scope/deferred reason.
6. **Review-rework loop**: L3 = mandatory iterations (default 3) in Phase 05; L2 = recommended (ask first); L1/L0 = none. One iteration = review → faithful findings record → triage → accepted rework → update 03/04.
7. **Stop rule**: if after the final L3 iteration the status is not APPROVED, record `Final Status: BLOCKED`, do not write 06, and report to the user.
8. **Fallback**: retry the peer path or a fresh session; if context is too large, retry with 04 Review Context + 01/02/03 + core files; if a mandatory L3 review cannot complete, record BLOCKED in 05 and do not write 06.
9. Identify the reviewer: `Reviewer: [tool] via [host]`. Record the opinion under `## External / Cross-model Review` in the **Phase 05** document — **faithful, no summarization**.
10. Cross-model agreement is a recommendation, not a decision — final verdict is reviewer + user.

---

## [Phase 00: Base Plan Template]

```markdown
# [Base Plan] {Feature Name}

Risk Level: <L1|L2|L3>
<!-- required: this cycle's max risk — the higher of the user-declared level and the risk the change globs
     imply. Replace <...> with one of L1/L2/L3. Knowledge write-back reads this exact `Risk Level: Lx` line
     to size the note (the durable per-cycle tier that survives session resume); the 06 acceptance-evidence
     report gate (`_cycle_risk`) also scans it as a fallback when no session-level risk was declared. Keep it current: if
     implementation grows past what 00 planned, raise this line. An unfilled placeholder reads as unknown,
     and write-back then defaults to a deep note. -->

## 0. Prior Knowledge
| Type | Note | Key Takeaway |
|------|------|--------------|

## 1. Summary (Goal & Scope)

## 2. Impact Analysis (Critical)
- [Component A]: ...
- [Component B]: ...

## 3. Technology & Risks

## 4. Final Conclusion & UX Guide

## 5. Document Mapping (Checklist)
```

---

## [Phase 01: Plan Template]

```markdown
# [Plan] {Feature Name}

## 1. User Stories & Requirements

## 2. Data Schema (Entities, DTOs)

## 3. API / Interface Specifications

## 4. Acceptance Matrix
| ID | User Requirement | Required Evidence | Owner | Required? |
|---|---|---|---|---|
| A1 | | test / manual smoke / screenshot / log / N/A reason | | yes |
```

---

## [Phase 02: Design Template]

```markdown
# [Design] {Feature Name}

## 1. Architecture & Interface Design

## 2. Sequence Diagrams

## 3. Error Codes & Exception Strategy
```

---

## [Phase 03: Implementation Guide Template]

```markdown
# [Implementation] {Feature Name}

## 0. Pre-Implementation Checklist
- [ ] File ownership assigned before source edits
- [ ] Acceptance IDs from Phase 01 mapped to implementation tasks
- [ ] Verification command plan recorded

## 1. File Ownership (Modified Files)

## 2. Implementation Checklists
- [ ] Feature list
- [ ] Test scenarios and validation method
- [ ] Code conventions

## 3. Acceptance Implementation Trace
| Acceptance ID | Implementation Task | Test / Manual Evidence Planned | Status |
|---|---|---|---|

## 4. Build & Test Results
```

---

## [Phase 04: Gap Analysis Template]

```markdown
# [Analyze] {Feature Name}

**Reviewer:** leader (responsible)  **Contributor:** qa (coverage)  **Date:** {YYYY-MM-DD}

> 04 issues no standalone verdict. The verdict is issued in 05.

## 1. Design vs. Implementation Gap (Match Rate: X%)

## 2. Missing Items & Deviations

## 3. Coverage Verification (qa)
- covered / not covered / intentionally excluded cases
- sufficiency vs design requirements; recommended additional scenarios

## 4. Acceptance Evidence Review
| Acceptance ID | User Requirement | Status (PASS/FAIL/NOT TESTED/N/A) | Evidence | Notes |
|---|---|---|---|---|

## 5. Review Context for External Model
### Original User Intent
### Key Decisions During Implementation
### Scope Changes / Deferred Items
### Known Risks / Open Questions
### Files the Reviewer Must Inspect
```

---

## [Phase 05: Expert Review Template]

```markdown
# [Expert Review] {Feature Name}

**Reviewer Role:** reviewer (synthesis) (+ cross-model reviewer when enabled)
**Review Date:** {YYYY-MM-DD}
**Final Status:** APPROVED / FAIL / BLOCKED
**Source:** 04-analyze gap findings + team output

## External / Cross-model Review
**Reviewer:** [tool] via host
**Inputs:** plan_docs/00·01·02·03·04 + component plan docs + implementation files
**Status:** COMPLETED / BLOCKED

### External Findings
[reviewer output verbatim — no summarization]

### Review Loop Iterations
| Iteration | External Result | Triage | Accepted Rework | Rejected/Deferred | 03/04 Updated | Status |
|:---:|:---|:---|:---|:---|:---:|:---|
| 1 | | | | | | |

### Reviewer Interpretation
- accepted / disputed (already-intended decisions) / deferred

### Acceptance Gate
| Acceptance ID | 04 Status | Reviewer Finding | Decision |
|---|---|---|---|

Required acceptance items with `FAIL` or `NOT TESTED` block `APPROVED`. Use `N/A`
only when the item was explicitly out of scope, deferred, or user-approved.

### Needs User Approval
| Item | Reason | Owner | Status |
|---|---|---|---|

### Final Status
APPROVED / FAIL / BLOCKED

> If not APPROVED after the final L3 iteration → `Final Status: BLOCKED`,
> do not write Phase 06.

## 1. Code Quality (SOLID, naming, dead code)
## 2. Domain/Architecture (per profile.components)
## 3. Security (auth, input validation, info leakage)
## 4. Performance & Concurrency
## 5. Convention Compliance (profile.conventions)

## 6. Review Scorecard
| Category | Score (1–5) | Key Issues |
|:---|:---:|:---|

## 7. Action Items
| Priority | Issue | Recommendation |
|:---:|:---|:---|
```

---

## [Phase 06: Final Report Template]

```markdown
# [Report] {Feature Name}

Loop-Run: {run_id}
Source-05: {root-relative path of the APPROVED Phase 05 doc}

## 1. Completion Summary

## 2. Value Delivered
| Problem | Solution | Effect | Core Value |
|:---|:---|:---|:---|

## 3. Lessons Learned & Future Tasks

## 4. Knowledge Capture (optional)
| Note | Action | Reason |
|:---|:---|:---|
```

`Loop-Run` copies the `run_id` from the APPROVED Phase 05 doc so the report declares
which review cycle it closes. The Stop-time retro gate reads this line to verify
`sage retro --check` ran for that run; omit it and the gate cannot bind the report
(warned under advisory, blocked under enforce).

---

## Related Rules
- `AGENT_GUIDE.md` — Risk & Workflow Gate
- `docs/agent/review-protocol.md` — reviewer resolution
- `profile.pdca` — phase set, per-level obligation, report/approve gate
