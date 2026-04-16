---
id: walkthrough-notification-preferences
version: 1.1.0
role: worked-example
---

# Walkthrough: The `notification-preferences` User-Facing Deliverable

An end-to-end mental walkthrough of the framework on a **user-facing**
deliverable. Supplements `walkthrough-mini-deliverable.md` (currency-
converter) — the two walkthroughs cover the `user_facing: false` and
`user_facing: true` execution modes respectively. If both walkthroughs
are reachable from the templates in `templates/`, the framework's
user-facing and non-user-facing paths both dogfood cleanly.

**Scenario.** A project has a notifications system and needs a user-
facing settings page where the user can toggle each notification type
(account, product-updates, marketing) on/off, with a save action that
persists to the user's profile and shows a success / failure toast.
The notifications system itself (the backend that sends notifications)
already exists; this deliverable is the UI + persistence layer only.

**Why this is user-facing.** The deliverable produces copy a user
reads (toggle labels, save confirmation, error messages), UX flows the
user walks (toggle → save → toast), accessibility surfaces (keyboard
nav, aria labels, focus order), and failure-visibility decisions (what
does the user see if save fails?). `user_facing: true` in the manifest.

**Four model families are configured** (same floor as v1.0.0 — the
Product family reuses one engineering family in a separate P10 session):

| Family           | shell | git | tests | doc index | Role in this deliverable           |
|------------------|:-----:|:---:|:-----:|:---------:|------------------------------------|
| `claude-opus`    |  ✓    |  ✓  |  ✓    |    ✓     | Author (A, C, D.4)                  |
| `claude-sonnet`  |  ✓    |  ✓  |  ✓    |    ✓     | Reviewer, verifier                  |
| `codex`          |  ✓    |  ✓  |  ✓    |    ✓     | Reviewer, meta-consolidator, Product reviewer (separate session per P10) |
| `gemini`         |  —    |  —  |  —    |    ✓     | Reviewer (doc-only), retro          |

With strict P3, every engineering review board (B.1, B.2, D.2) uses
three non-author families (claude-sonnet, codex, gemini). Because
`user_facing: true`, each board additionally dispatches a Product
reviewer (codex in a separate session). The author family claude-opus
remains excluded from its own review.

**Adoption-floor note.** This walkthrough demonstrates the v1.1
"Product family overlaps engineering family" pattern: codex plays
Adversarial AND Product on B.1, in two separate worker sessions with
distinct dispatches (see `framework.md` § P3 user-facing extension).
Adopters who prefer a strict 5-family configuration (claude-opus +
claude-sonnet + codex + gemini + one more for Product) may configure
their manifest that way; v1.1 does not mandate it.

---

## Pre-A choice: which entry point?

The scenario offers at least two candidates for pre-A:

- **`-A.proposal`** — if the team debates modal vs dedicated-page,
  single-save vs per-toggle-save, or whether marketing notifications
  should exist at all. Template `16-proposal-review.md`.
- **`-A.validation`** — if a staging deployment already has a placeholder
  settings page and the team wants to observe real user flow before
  specifying. Template `18-validation-run.md`.

For this walkthrough we pick **Proposal Review**: the team has three
candidate designs (dedicated page / modal-dropdown / inline-banner) and
wants to converge before spending spec time.

Manifest declares:

```yaml
user_facing: true
pre_a:
  entry: proposal
  artifact_path: docs/reviews/notification-preferences-proposal-verdict.md
```

---

## Phase -A.proposal — Proposal Review (template 16)

Per playbook §13.4, Proposal Review uses a 2-lens board. The framework
P3 carve-out (framework.md § P3) means ≥3 families is NOT required
here; one non-author family running the single consolidated Proposal
Review template is sufficient.

`codex` is dispatched with `16-proposal-review.md`. In one session it
applies both lenses: Product (adversarial posture) and Technical
(alignment posture). Output:

`docs/reviews/notification-preferences-proposal-verdict.md`

Example finding (high-signal Product-vs-Technical disagreement):

- **Product lens says:** "Dedicated settings page is over-engineered
  for 3 toggles; modal-dropdown is simpler and matches user expectation
  from adjacent products."
- **Technical lens says:** "Modal-dropdown duplicates the settings-page
  persistence layer; dedicated page reuses existing settings
  infrastructure."

Per playbook §13.4 guidance, this disagreement is surfaced explicitly.
Verdict: **Revise and re-review** — proposal updates to propose a
dedicated settings page with a single save (aligning to Technical's
infrastructure reuse) but pared down to fit the scope (Product's
over-engineering concern partially addressed).

Round 2 of Proposal Review: codex dispatched again; verdict **Proceed
to Phase A**. Proposal doc frozen; Phase A dispatches with the
validated direction as scope-lock.

---

## Phase 0 — Scope lock (derived from Proposal Review output)

Allowed paths: `src/settings/notifications/`,
`tests/test_notifications.py`. Forbidden paths: `src/auth/`,
`migrations/`, `.github/`.

Cardinality:
- Public API exports exactly `NotificationPreferences` component and
  `save_preferences(user_id, prefs)` function.
- Three notification types exactly: account, product-updates, marketing.
- Each toggle has exactly one aria-label.

Gate prerequisites: 10 entries spanning the 6 categories + one
user-facing category addition if the project's gate verifier adds it
(v1.1 does not mandate a 7th category; the 6 categories still cover
user-facing concerns via test / scope / cardinality).

---

## Phase A — Spec authoring (template 12)

`claude-opus` authors the spec via `12-spec-author.md`. Ten sections
including explicit user-facing coverage: UX flow diagram, copy
inventory (all user-visible strings inlined), accessibility matrix
(keyboard nav map, aria labels, focus order), failure-mode
visibility table (save fails → toast says X; network gone → toast says
Y; duplicate-save-click → debounce).

**Diagram-gate check (A.5).** Two diagrams: state machine (idle →
editing → saving → saved / failed → editing) and component tree
(SettingsPage → NotificationPreferences → ToggleRow × 3 + SaveButton +
Toast). Every component named in diagrams appears in prose.

---

## Phase B.1 — Spec review with Product lens (templates 03, 04, 05, 19)

Per `user_facing: true`, the B.1 review board is **four-lens**:

| Family          | Role         | Template | Session ID           |
|-----------------|--------------|----------|----------------------|
| `claude-sonnet` | Peer         | `03`     | B.1-claude-sonnet-peer |
| `gemini`        | Alignment    | `04`     | B.1-gemini-alignment |
| `codex`         | Adversarial  | `05`     | B.1-codex-adversarial |
| `codex`         | Product      | `19`     | **B.1-codex-product** (separate P10 session from B.1-codex-adversarial) |

Note the two `codex` sessions are distinct dispatches — separate
prompts, separate worker invocations, separate commit authors.
`verify-p3.sh` confirms the Product-presence requirement holds AND
that no single session holds two roles. Orchestrator dispatches all
four in parallel.

Each produces a verdict. Per manifest `artifacts.family_verdict` and
`artifacts.product_verdict`:

- `docs/reviews/notification-preferences-B.1-claude-sonnet-peer.md`
- `docs/reviews/notification-preferences-B.1-gemini-alignment.md`
- `docs/reviews/notification-preferences-B.1-codex-adversarial.md`
- `docs/reviews/notification-preferences-B.1-codex-product.md`

Say `codex` (Product) raises a blocker via Template 19 §2.1
(spec-declared surface inventory): "The failure-visibility section
documents a toast for save-failed, but the spec's accessibility matrix
does not include `aria-live` semantics for that toast. Screen-reader
users cannot be notified of save failures if the implementation
follows the spec literally. Evidence: `static-inspection` —
`spec §7 Failure visibility` lists the toast but the Phase A
accessibility matrix (§5) has no row for `role=alert` or
`aria-live=polite` on the toast container." Blocker.

Template 19 §2.2 (spec-vs-implementation cross-reference) is marked
`n/a (Phase B — no implementation yet)` per the template's phase-aware
guidance. It would be exercised at Phase D.2 once the implementation
lands. This walkthrough's Phase B.1 Product review relies entirely on
static inspection of the spec text and matrices; prototype testing is
out of scope at Phase B unless the Phase A spec explicitly includes a
runnable prototype.

## Phase B.3 — Meta-consolidation (template 06, 4-row intake)

`codex` (in yet another separate session, now as meta-consolidator)
runs `06-meta-consolidator.md` with `<USER_FACING>` = `true` and
`<PRODUCT_VERDICT_PATH>` = `docs/reviews/notification-preferences-B.1-codex-product.md`.

Output: `docs/reviews/notification-preferences-B.3-verdict.md`
(canonical path, no `<family>` / `<role>` placeholders per invariant 10).

Family verdict table has **four rows** (one per lens). Preserved
blocker: the live-region semantics finding from codex-Product.
Canonical verdict: **Needs Fixes**.

`claude-opus` updates the spec to specify `aria-live="polite"` on the
toast container, adds a test for screen-reader announcement using a
pseudo-aria snapshot. Re-run B → **Approve** (verdict includes 4 rows
per the user-facing intake; Product row now Approve).

---

## Phase C — Implementation (template 13)

`claude-opus` implements via `13-implementation-author.md`. Output:
React / Vue / framework-agnostic component files in
`src/settings/notifications/`, tests in `tests/test_notifications.py`.

**Phase C smoke checks** include:
- Module imports
- Component renders with all 3 toggles
- Save function persists to the mocked user profile

---

## Phase D.2 — Code review with Product lens (four-lens, again)

Four-lens review board, rotated families to avoid repeat-lens per
deliverable:

| Family          | Role         | Template | Notes |
|-----------------|--------------|----------|-------|
| `gemini`        | Peer         | `03`     | doc-only; static-inspection |
| `claude-sonnet` | Alignment    | `04`     | |
| `codex`         | Adversarial  | `05`     | |
| `claude-sonnet` | Product      | `19`     | separate P10 session from claude-sonnet-alignment |

`claude-sonnet` (Product) raises a finding: "Error toast uses `role=alert`
which is appropriate for save failures, but the same toast component
is also used for success confirmation where `role=alert` is wrong
(interrupts the user unnecessarily). `direct-run` reproduction: manual
test with NVDA on the reference build."

## Phase D.3 — Consolidation (4-row)

Four-row canonical verdict with the role=alert finding preserved.
Verdict: **Needs Fixes**.

## Phase D.4 — Fix (template 14)

`claude-opus` splits the toast into two variants: success toast uses
`role=status`, error toast uses `role=alert`. Regression test asserts
the semantic role per variant. Fix summary:
`docs/reviews/notification-preferences-D.4-fix-summary.md`.

## Phase D.5 — Verification (template 15)

Three non-author families verify the fix. The Product family (claude-
sonnet) does NOT have a separate verifier slot in v1.1 — Phase D.5
remains a 3-family engineering verification. The Product concern was
already captured as a D.3 blocker and closed via D.4; D.5 confirms
fixes, not re-runs Product review.

## Phase D.6 — Final-approval gate

Gate prerequisites table, same 6 categories. Additional user-facing
concerns (accessibility regression test passes, copy approved,
failure-visibility live-region works) are covered under the existing
categories — no new category required. Gate: **PASSED** (assuming
all 10 yes).

Merge per P8 (fresh non-local clone, `--no-ff`).

---

## Phase E — Retrospective (template 08)

`gemini` runs `08-retrospective.md`. Typical user-facing learnings:

- The Product lens caught two accessibility findings that the three
  engineering lenses missed (live-region semantics, role=alert
  misuse). Without Product, both would have shipped.
- The same-family-separate-session pattern (codex plays Adversarial
  and Product on B.1 in two sessions) felt redundant to configure but
  produced genuinely different findings — the lens preamble,
  not the family, drove the finding type.
- Proposal Review's explicit Product-vs-Technical disagreement block
  surfaced a tension (scope pressure vs infrastructure reuse) that
  would have resurfaced mid-spec as scope creep if not addressed in
  pre-A.

Retrospective feeds the next user-facing deliverable's manifest.

---

## What this walkthrough tests in the framework

| Concern                                                              | Checked by |
|-----------------------------------------------------------------------|-----------|
| Every user-facing-specific template is reachable                     | Templates 16, 19 dispatched above |
| Pre-A Proposal Review produces a Phase A scope lock                  | `-A.proposal` Round 2 `Proceed to Phase A` |
| 4-verdict meta-consolidation works end-to-end                         | Phase B.3 4-row canonical verdict |
| P3 user-facing extension is executable with 4 families (not 5)       | codex plays Adversarial + Product in separate sessions |
| `verify-p3.sh` enforces both 3-engineering AND Product-presence       | Manifest passes `verify-p3.sh`; Product role present for B.1/B.2/D.2 |
| Schema validates user-facing manifest                                | `scripts/verify-schema.sh` on this walkthrough's manifest |
| Product lens finds issues engineering lenses miss                     | Live-region / role=alert findings caught by Product, not Peer/Alignment/Adversarial |

If a future walkthrough reveals a user-facing path that cannot be
executed with only the bundle's templates, that is a framework gap and
bumps a patch version.
