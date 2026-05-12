---
deliverable_id: folio-correspondence-ingest-v1-3-0
phase: B.1
role: peer
family: claude-sonnet
status: completed
evidence_labels_used:
  - direct-run
---

# B.1 Peer Review: folio-correspondence-ingest-v1-3-0

## Summary

This review assesses whether the Phase A spec (`folio-correspondence-ingest-v1-3-0_phase_a_spec.md`) and manifest (`frameworks/manifests/folio-correspondence-ingest-v1-3-0.yaml`) are adequate to drive the slice without relying on stale evidence. Source authority: `docs/validation/strict_p3_rerun_2026_05_12/pre_a_triage.md`.

## Stale Evidence Check

Clean. The pre-A triage explicitly states: "prior `folio_*_v1_*` artifacts and the preserved dirty attempt are implementation history only; they are not lifecycle evidence for this rerun." The Phase A spec reinforces this with its own non-goal: "Do not count any old artifacts from the prior failed closeout as evidence." No lifecycle evidence is drawn from the prior attempt.

## Spec Adequacy Assessment

**Scope authority is properly anchored.** The spec names the triage doc as its scope authority and maps cleanly to issues #61 (native EML ingest, new `correspondence` type, attachment cataloging) and #64 (Message-ID overlap continuation/versioning, `--as-new-entry` override). The triage contains full issue bodies, so the implementation author has access to the detailed behavioral spec even though the Phase A spec itself is terse.

**Acceptance criteria are thin but traceable.** The three bullets cover the essential contract: (1) new CLI entry points, (2) parsing scope including `message_ids`, and (3) continuation/versioning with override. An implementation author must fall back to the issue bodies for detail — noise stripping rules, attachment sha256 schema, branch strategy defaults, body-hash fallback for lost Message-IDs — none of which appear in the spec. This is acceptable given the issue bodies are embedded in the triage doc, but the spec would be stronger if it called out the key behavioral commitments explicitly (e.g., which edge cases from #64 are in scope vs. deferred).

**Implementation surface is plausible but has a gap worth noting.** The spec lists `folio/correspondence.py` as the new module and scopes changes to `folio/cli.py`, `folio/ingest.py`, `folio/tracking/registry.py`, and the two test files. The manifest's `allowed_paths` matches this surface. However, correspondence frontmatter rendering (fields like `sender`, `recipients_to`, `thread_message_count` specified in issue #61) will require either extending `folio/output/frontmatter.py` or encapsulating all output logic inside `folio/correspondence.py`. Neither `folio/output/frontmatter.py` nor `folio/output/interaction_markdown.py` appears in the allowed paths. If the implementation author needs to touch those files, it will generate a scope violation. The spec should clarify that `folio/correspondence.py` owns its own output rendering, or add the relevant output paths.

## Manifest Quality Assessment

**Manifest version and lifecycle fields are correct.** `manifest_version: 1.6.0` and `lifecycle_receipt_inventory_path` are both present, satisfying strict-P3 requirements.

**Cardinality assertions are appropriately scoped.** The assertion checks for `folio/correspondence.py` existence and the symbols `ingest-email|message_ids|email_thread|as-new-entry` across `folio` and `tests`. These four symbols map directly to the four key contracts of the slice and will prevent partial implementations from passing the gate.

**Gate prerequisites are structurally sound.** The six gates (G-test-1, G-scope-1, G-cardinality-1, G-verdict-1, G-blocker-1, G-branch-1) cover test passage, review-board directory presence, cardinality anchors, three-family D.5 verifier count, D.3 blocker clearance, and branch identity. This is complete coverage for a strict-P3 slice.

**Model assignments are consistent with the framework.** Phase A: claude-opus spec-author. B.1: claude-sonnet peer, codex alignment, gemini adversarial. C: claude-opus implementation-author. D.2–D.6: correct. No anomalies.

**Smoke checks and regression guards.** Phase C smoke check runs the two focused test files. Phase D.6 smoke check runs `verify-lifecycle`. `regression_guards` is empty — acceptable for a net-new module with no pre-existing test surface, but worth confirming no existing EML-adjacent tests exist in the suite.

## Observations (Non-Blocking)

1. **Output path ambiguity** (`folio/output/frontmatter.py`): Clarifying whether `folio/correspondence.py` is self-contained for rendering, or whether output files need to be added to `allowed_paths`, would prevent a scope-violation surprise at Phase C. Currently unresolved by either the spec or the manifest.

2. **Acceptance criteria granularity**: Issue #64 specifies multiple branch/forward strategies (configurable `branch_strategy`, `forwarded_as_continuation`) and a body-hash fallback for malformed Message-IDs. None of these appear in the spec's three bullets. The Phase C implementation author will have to make independent scope decisions on these. A one-line scope note in the spec ("implement `branch_strategy: new_entry` default and body-hash fallback per #64") would reduce ambiguity.

3. **`--extract-attachments` flag**: Issue #61 proposes an opt-in flag for extracting attachment bodies into the registry. The spec's bullet ("Parse … attachments") is ambiguous on whether this flag is in scope. The cardinality assertion does not check for it. Intentional deferral should be stated explicitly in the non-goals.

## Verdict

approve

The spec and manifest are adequate to drive the implementation slice. The pre-A triage provides the full issue context, stale evidence is cleanly excluded, the manifest lifecycle fields are correct, and the cardinality assertions anchor the core contract. The noted concerns — output path ambiguity and thin acceptance criteria for #64 edge cases — are observations for the Phase C author to resolve, not blockers that prevent implementation from starting. No changes are required to proceed to Phase C.
