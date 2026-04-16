# Walkthrough — Pre-A Triage (Template 17)

Micro-walkthrough demonstrating `templates/17-triage.md` end to end on a
small hypothetical backlog. Shipped in v1.2 to close the PEER-SF2
deferral from the v1.1.0 review board (walkthrough dogfood for
Templates 17 and 18).

Non-normative: this file is a scaffolding demonstration, not a
production deliverable artifact. Identifiers and counts are
illustrative.

---

## Starting state

**Deliverable:** `currency-converter-audit` (a triage on a pre-existing
`currency-converter` module)

**Triage input file** (`<TRIAGE_INPUT_PATH>`):
`docs/triage/2026-04-currency-audit-findings.md`

```markdown
# Currency module — audit findings

| # | Finding | Category | Reporter | Date |
|---|---------|----------|----------|------|
| F1 | ISO table drops trailing currencies when > 40 entries | bug | user report | 2026-04-02 |
| F2 | `convert()` does not validate negative amounts | security-adjacent | static scan | 2026-04-05 |
| F3 | Rename `CURRENCIES` → `ISO_4217_TABLE` for clarity | tech-debt | dev comment | 2026-03-20 |
| F4 | Add caching layer to repeated lookups | performance | benchmark | 2026-04-10 |
| F5 | Docs don't mention supported rate sources | docs | customer email | 2026-03-30 |
```

---

## Dispatch (Pre-A.triage, 3-lens)

Per `framework.md § P3 pre-A carve-out`, triage uses the standard
3-lens board (Peer + Alignment + Adversarial). P3's ≥3-family floor
applies because Template 17 satisfies it (playbook §12.4).

**Manifest snippet:**
```yaml
pre_a:
  entry: triage
  artifact_path: docs/triage/2026-04-currency-audit-findings.md
model_assignments:
  - phase: "-A.triage"
    assignments:
      claude-sonnet:  peer
      codex:          alignment
      gemini:         adversarial
artifacts:
  triage_report: docs/triage/2026-04-currency-audit-triage.md
```

The orchestrator dispatches three parallel sessions using Template 17.

---

## Family rulings

**Peer lens** (claude-sonnet) — categorizes each finding by scope-fit
quality:

| # | Ruling | Rationale |
|---|--------|-----------|
| F1 | In-Scope | clear bug; single-function fix |
| F2 | In-Scope + fast-patch | missing input validation; 1-line addition + regression test; suitable for C-direct |
| F3 | Deferred | cosmetic; defer to next deliverable unless grouped with F1 |
| F4 | Deferred | introduces caching layer — architectural; needs its own spec |
| F5 | In-Scope | doc fix; couple with F1 fix |

**Alignment lens** (codex) — cross-references prior decisions + project
roadmap:

| # | Ruling | Citation |
|---|--------|----------|
| F1 | In-Scope | matches 2026 Q2 currency scope (roadmap § 3.1) |
| F2 | In-Scope + fast-patch | no prior-decision conflict; aligned with `forbidden_symbols` stance |
| F3 | Deferred | renaming conflicts with v1.0.0 API stability promise (ADR-004); needs v2 major |
| F4 | Rejected | caching was explicitly deferred to a separate performance deliverable (roadmap § 4.2) |
| F5 | In-Scope | matches docs convention (prior decision PRD-2025-11) |

**Adversarial lens** (gemini) — attacks each finding for hidden risk:

| # | Ruling | Risk flagged |
|---|--------|--------------|
| F1 | In-Scope | the ">40" threshold is load-bearing — bug may mask a worse issue at >100 entries |
| F2 | In-Scope + fast-patch | watch for off-by-one on zero (0 is not negative; must accept) |
| F3 | Rejected | rename churn breaks downstream imports; ADR-004 compat promise; no upside |
| F4 | Deferred | caching introduces stale-rate risk — wrong answer is worse than slow |
| F5 | In-Scope | user-email source is ambiguous — confirm the real question before docs answer the wrong one |

---

## Consolidation (playbook §12.4, 3-lens disposition)

Orchestrator reads the three lens verdicts and emits a per-finding
disposition. Template 17's disposition enum:
`In-Scope | In-Scope + fast-patch | Deferred | Rejected`.

| # | Peer | Alignment | Adversarial | Consolidated |
|---|------|-----------|-------------|--------------|
| F1 | In-Scope | In-Scope | In-Scope | **In-Scope** (unanimous) |
| F2 | In-Scope + fast-patch | In-Scope + fast-patch | In-Scope + fast-patch | **In-Scope + fast-patch** (unanimous; route to C-direct per playbook §12.5 / generator-spec invariant 17) |
| F3 | Deferred | Deferred | Rejected | **Deferred** (Peer + Alignment concur; Adversarial's reject is absorbed into the defer — revisit only on v2 major) |
| F4 | Deferred | Rejected | Deferred | **Deferred** (to performance deliverable — Alignment's reject is re-framed as "not this deliverable") |
| F5 | In-Scope | In-Scope | In-Scope + (clarify) | **In-Scope** with open question: confirm question scope with reporter before docs fix |

---

## Overall triage verdict (Template 17 §7)

**Proceed to Phase A** for the In-Scope set (F1, F5), **Proceed to
Phase C-direct** for the fast-patch (F2), **Deferred** set recorded
in the next deliverable's backlog (F3, F4).

Fast-patch authorization per generator-spec invariant 17: F2 is a
single-function validation addition + regression test; no spec
pass needed. Directly enters Phase C with a minimal manifest that
declares only the C + D.2 phases.

---

## Artifacts produced

- `docs/triage/2026-04-currency-audit-triage.md` — the triage verdict
  artifact following Template 17's output scaffolding.
- Tracker updates for each finding (phase `-A.triage` → disposition).
- A Phase A manifest authoring task for F1 + F5 (In-Scope) with
  `cardinality_assertions` covering the threshold > 40 case.
- A Phase C-direct manifest for F2 (fast-patch) with a
  regression-test requirement in the gate.

## End

This walkthrough stays under 200 lines by staying tight on a single
illustrative backlog. A real triage may span 20+ findings; the
Template 17 dispatch + 3-lens consolidation pattern scales linearly.
