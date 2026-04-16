#!/usr/bin/env bash
# verify-circuit-breaker.sh — validate review_rounds schema and report
# per-phase circuit-breaker state on a manifest-shaped YAML.
#
# v1.2+ circuit-breaker rule: for any phase with ≥2 rounds, CB fires
# if round N+1's preserved_blocker_ids OVERLAPS round N's (same blockers
# cycling = stagnation). If all round N+1 IDs are NEW (no overlap), CB
# is quiescent (a converging review in an improved artifact).
#
# Inputs: one or more YAML paths. Default (no args): the two bundled
# example manifests.
#
# Exits 0 on validation pass (CB state reported; a fire is NOT an exit
# failure — it's a state the orchestrator acts on). Exit 1 on schema
# violation (missing field, wrong type, bad round number). Exit 2 on
# missing dep / unreadable file.

set -euo pipefail

here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
bundle="$(cd "$here/.." && pwd)"

if [[ $# -eq 0 ]]; then
  set -- \
    "$bundle/manifest/example-manifest.yaml" \
    "$bundle/manifest/example-user-facing-manifest.yaml"
fi

if ! command -v python3 >/dev/null 2>&1; then
  echo "verify-circuit-breaker: python3 is required" >&2
  exit 2
fi

python3 - "$@" <<'PY'
import sys
import yaml
from collections import defaultdict

paths = sys.argv[1:]
overall_rc = 0
total_rounds = 0
total_fires = 0
total_quiescent = 0

for path in paths:
    try:
        with open(path) as f:
            m = yaml.safe_load(f)
    except FileNotFoundError:
        print(f"verify-circuit-breaker: {path}: file not readable", file=sys.stderr)
        overall_rc = 2
        continue

    rounds = (m or {}).get("review_rounds") or []
    if not rounds:
        print(f"verify-circuit-breaker: {path}: no review_rounds declared (no-op, OK)")
        continue

    # Schema validation: each entry must have phase, round, preserved_blocker_ids.
    for i, entry in enumerate(rounds):
        if not isinstance(entry, dict):
            print(f"verify-circuit-breaker: {path}: review_rounds[{i}] is not a mapping", file=sys.stderr)
            overall_rc = 1
            continue
        missing = [k for k in ("phase", "round", "preserved_blocker_ids") if k not in entry]
        if missing:
            print(
                f"verify-circuit-breaker: {path}: review_rounds[{i}] missing required field(s) {missing}",
                file=sys.stderr,
            )
            overall_rc = 1
            continue
        if not isinstance(entry["round"], int) or entry["round"] < 1:
            print(
                f"verify-circuit-breaker: {path}: review_rounds[{i}] round must be integer ≥ 1 (got {entry['round']!r})",
                file=sys.stderr,
            )
            overall_rc = 1
        if not isinstance(entry["preserved_blocker_ids"], list):
            print(
                f"verify-circuit-breaker: {path}: review_rounds[{i}] preserved_blocker_ids must be list (got {type(entry['preserved_blocker_ids']).__name__})",
                file=sys.stderr,
            )
            overall_rc = 1
            continue
        for j, bid in enumerate(entry["preserved_blocker_ids"]):
            if not isinstance(bid, str):
                print(
                    f"verify-circuit-breaker: {path}: review_rounds[{i}].preserved_blocker_ids[{j}] must be string",
                    file=sys.stderr,
                )
                overall_rc = 1

    if overall_rc != 0:
        continue

    # Group by phase, order by round.
    by_phase = defaultdict(list)
    for entry in rounds:
        by_phase[entry["phase"]].append(entry)
    for phase, entries in by_phase.items():
        entries.sort(key=lambda e: e["round"])

        # Detect duplicate round numbers within a phase.
        seen_rounds = set()
        dupes = set()
        for e in entries:
            if e["round"] in seen_rounds:
                dupes.add(e["round"])
            seen_rounds.add(e["round"])
        if dupes:
            print(
                f"verify-circuit-breaker: {path}: phase {phase} has duplicate round numbers {sorted(dupes)}",
                file=sys.stderr,
            )
            overall_rc = 1
            continue

        # Report state and CB decision for this phase.
        if len(entries) == 1:
            single = entries[0]
            print(
                f"verify-circuit-breaker: {path}: phase {phase} round {single['round']}: "
                f"{len(single['preserved_blocker_ids'])} preserved (single round — no CB comparison)"
            )
            total_rounds += 1
            continue

        total_rounds += len(entries)
        for prev, curr in zip(entries, entries[1:]):
            prev_ids = set(prev["preserved_blocker_ids"])
            curr_ids = set(curr["preserved_blocker_ids"])
            overlap = prev_ids & curr_ids
            if overlap:
                total_fires += 1
                print(
                    f"verify-circuit-breaker: {path}: phase {phase} round "
                    f"{prev['round']}→{curr['round']}: CB FIRES — "
                    f"{len(overlap)} blocker ID(s) cycling: {sorted(overlap)}"
                )
            else:
                total_quiescent += 1
                print(
                    f"verify-circuit-breaker: {path}: phase {phase} round "
                    f"{prev['round']}→{curr['round']}: CB quiescent — "
                    f"{len(curr_ids)} new blocker ID(s) surfaced, zero carry-forward"
                )

if overall_rc == 0:
    print(
        f"verify-circuit-breaker: OK "
        f"(rounds analyzed: {total_rounds}; CB fires: {total_fires}; CB quiescent: {total_quiescent})"
    )
sys.exit(overall_rc)
PY
