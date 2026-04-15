#!/usr/bin/env bash
# verify-pre-a.sh — static coherence check for the v1.1 pre_a block.
#
# For each example manifest, if `pre_a` is declared, assert:
#   1. `pre_a.entry` is one of {proposal, triage, validation}.
#   2. `pre_a.artifact_path` is a non-empty string.
#   3. The corresponding `artifacts.<entry>_verdict` /
#      `artifacts.<entry>_report` field is declared in the manifest (so
#      the generator can route the pre-A artifact to a stable path).
#   4. (v1.1 strengthened — Codex review) `pre_a.artifact_path` equals
#      the corresponding `artifacts.<entry>_*` field exactly. Without
#      this check, the worker can write to one path while the
#      orchestrator gates on another (route-vs-write divergence).
#
# Runtime presence of the artifact at `artifact_path` (the "exists
# before Phase A" half of generator-spec invariant 16) remains the
# orchestrator's responsibility — this script does not run from a live
# deliverable's worktree, only from the bundle's example manifests, so
# it cannot stat the artifact at runtime. Adopters' orchestration code
# (or the manifest generator at v2) MUST add the runtime existence
# check before dispatching Phase A.
#
# Manifests without a `pre_a` block are accepted silently (pre-A is
# optional).
#
# Dependency: `python3` with pyyaml.
#
# Exits 0 on success, non-zero with diagnostics otherwise.

set -euo pipefail

here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
bundle="$(cd "$here/.." && pwd)"

manifests=(
  "$bundle/manifest/example-manifest.yaml"
  "$bundle/manifest/example-user-facing-manifest.yaml"
)

python3 - "${manifests[@]}" <<'PY'
import sys, yaml

paths = sys.argv[1:]
overall_rc = 0
pre_a_checked = 0

# Mapping from pre_a.entry → expected artifacts.* field name.
entry_to_artifact_field = {
    "proposal":   "proposal_verdict",
    "triage":     "triage_report",
    "validation": "validation_run_report",
}

for path in paths:
    with open(path) as f:
        m = yaml.safe_load(f)

    pre_a = m.get("pre_a")
    if pre_a is None:
        # Optional — silent pass.
        continue

    pre_a_checked += 1

    entry = pre_a.get("entry")
    artifact_path = pre_a.get("artifact_path")

    if entry not in entry_to_artifact_field:
        print(
            f"verify-pre-a: {path}: pre_a.entry must be one of "
            f"{sorted(entry_to_artifact_field)}; got {entry!r}",
            file=sys.stderr,
        )
        overall_rc = 1
        continue

    if not isinstance(artifact_path, str) or not artifact_path.strip():
        print(
            f"verify-pre-a: {path}: pre_a.artifact_path must be a "
            f"non-empty string; got {artifact_path!r}",
            file=sys.stderr,
        )
        overall_rc = 1
        continue

    expected_field = entry_to_artifact_field[entry]
    artifacts = m.get("artifacts", {})
    if expected_field not in artifacts or not artifacts.get(expected_field):
        print(
            f"verify-pre-a: {path}: pre_a.entry={entry!r} requires "
            f"artifacts.{expected_field} to be declared (and non-empty), "
            f"so the generator can route the pre-A artifact. Got "
            f"artifacts.{expected_field}={artifacts.get(expected_field)!r}",
            file=sys.stderr,
        )
        overall_rc = 1
        continue

    # Path consistency (v1.1 strengthened — Codex review): pre_a.artifact_path
    # MUST equal artifacts.<entry>_field. If the worker writes to one path and
    # the orchestrator gates on a different path, dispatch silently fails.
    declared_artifact = artifacts.get(expected_field)
    if artifact_path != declared_artifact:
        print(
            f"verify-pre-a: {path}: pre_a.artifact_path "
            f"({artifact_path!r}) must equal artifacts.{expected_field} "
            f"({declared_artifact!r}). The worker writes to "
            f"pre_a.artifact_path; the orchestrator routes via "
            f"artifacts.{expected_field}; divergence silently breaks "
            f"dispatch.",
            file=sys.stderr,
        )
        overall_rc = 1
        continue

if overall_rc == 0:
    print(f"verify-pre-a: OK ({pre_a_checked} manifest(s) with pre_a block validated; others skipped)")
sys.exit(overall_rc)
PY
