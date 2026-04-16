# Walkthrough — Pre-A Validation Run (Template 18)

Micro-walkthrough demonstrating `templates/18-validation-run.md` end
to end on a small hypothetical observation-run. Shipped in v1.2 to
close the PEER-SF2 deferral from the v1.1.0 review board alongside
`walkthrough-triage.md`.

Per playbook §15.3, a Validation Run is an **observation protocol
over deployed code** — not a review board, not a prototype-measure-
decide loop. The output is a Run Report with a verdict of
`Run clean | Run inconclusive | Run exposed defect`.

Non-normative scaffolding demonstration.

---

## Starting state

**Deliverable:** `currency-converter-rate-freshness` — the team
suspects the deployed `convert()` function uses stale rates after a
long-running process, but has no direct report. A Validation Run is
scoped before any spec pass.

**Validation-run input file** (`<VALIDATION_RUN_INPUT_PATH>`):
`docs/runs/2026-04-rate-freshness-observation-plan.md`

```markdown
# Validation Run — rate freshness

## Target
Deployed `currency-converter` service at `api.example.com/convert`.

## Hypothesis
After a process runs for ≥ 4 hours, `convert()` returns values that
are stale by more than the declared freshness guarantee (15 minutes).

## Measurements
- Call `/convert` once per minute for 5 hours under a single process.
- For each call: record the returned rate and compare against the
  fresh rate from the upstream source at the same timestamp.
- Flag any deviation exceeding the 15-minute guarantee.

## Budget
5 hours wall-clock, 300 API calls (~$0.02), single dedicated host.

## Out of scope
- Root-cause analysis. This is observation only.
- Performance (latency is not the measurement target).
- Multi-process / distributed-cache consistency.
```

---

## Dispatch (Pre-A.validation)

Per `framework.md § P3 pre-A carve-out`, Validation Run has no P3
floor — it is a single-reviewer observation protocol, not a review
board.

**Manifest snippet:**
```yaml
pre_a:
  entry: validation
  artifact_path: docs/runs/2026-04-rate-freshness-observation-plan.md
model_assignments:
  - phase: "-A.validation"
    assignments:
      codex: validation-run-author
artifacts:
  validation_run_report: docs/runs/2026-04-rate-freshness-run-report.md
```

One reviewer (Codex in this example; any capability-sufficient family
works). The reviewer executes the observation plan with direct-run or
orchestrator-preflight evidence — `static-inspection` is not
sufficient for a Validation Run verdict (playbook §15.3; Template 18
enforces).

---

## Execution

**Runtime facts** (orchestrator-verified and injected per Template 02):

- Target: `https://api.example.com/convert`
- Upstream reference: `https://rates.example.com/latest`
- Process host: dedicated worker, no cache warming.
- Measurement cadence: 1 call / minute for 300 minutes.

The reviewer runs the measurements, records each data point, and
computes per-minute deviation:

| Minute bucket | Deviation (bps) | Within 15-min guarantee? |
|---------------|-----------------|--------------------------|
| 0–60          | 0–2             | yes                      |
| 60–120        | 0–5             | yes                      |
| 120–180       | 1–8             | yes                      |
| 180–240       | 12–28           | **no — 3 violations**    |
| 240–300       | 22–41           | **no — 5 violations**    |

---

## Verdict (Template 18 §6)

**Run exposed defect** — the 15-minute guarantee held for the first
3 hours of runtime but fails after the 4-hour mark with a
deviation trend that correlates with process uptime rather than rate
volatility. Evidence class: `direct-run` (every measurement was an
observed API call with captured response body).

The Validation Run is NOT a fix pass. It produces:

1. A Run Report following Template 18's output scaffolding
   (`<validation_run_report>` path).
2. An incident-postmortem referral (Template 09) — the defect is
   in-production, so an incident process owns the immediate response.
3. A follow-up deliverable scope recommendation: `currency-converter-
   rate-cache-invalidation` (the fix) should enter Phase A as a
   standalone deliverable, NOT a fast-patch (defect is non-trivial
   and may affect distributed consistency).

---

## Artifacts produced

- `docs/runs/2026-04-rate-freshness-run-report.md` — the Run Report.
- An incident postmortem dispatch (parallel, not blocking this
  walkthrough).
- A Phase A manifest authoring task for the follow-up fix deliverable.

---

## Contrast with Triage (Template 17)

| | Triage (T17) | Validation Run (T18) |
|---|--------------|----------------------|
| Pre-A entry | `-A.triage` | `-A.validation` |
| Input | Backlog of findings | Observation plan over deployed code |
| Lens count | 3 (Peer / Alignment / Adversarial) | 1 (single observation-run author) |
| P3 floor | applies (covered by 3-lens) | waived (observation, not review) |
| Evidence | Any class, per lens | direct-run or orchestrator-preflight only |
| Verdict | In-Scope / In-Scope + fast-patch / Deferred / Rejected | Run clean / Run inconclusive / Run exposed defect |
| Typical next phase | Phase A (scope drafted) or Phase C-direct (fast-patch) | Phase A (fix spec) or incident postmortem |

Both feed `framework.md § P3 pre-A carve-out` — neither gates a
phase-advance review board; both precede Phase A.

## End

Real Validation Runs commonly span several days (load tests,
production observation windows). The protocol + verdict shape
remains identical; only the wall-clock budget and sample size
change.
