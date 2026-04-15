#!/usr/bin/env bash
# verify-gate-categories.sh — the example manifest's `gate_prerequisites`
# must include at least one entry in each of the six required categories.
#
# Categories: test, scope, cardinality, verdict-presence, blocker-closure,
# branch.
#
# Dependency: python3 + pyyaml.

set -euo pipefail

here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
bundle="$(cd "$here/.." && pwd)"
manifest="$bundle/manifest/example-manifest.yaml"

python3 - "$manifest" <<'PY'
import sys, yaml

required = {"test", "scope", "cardinality", "verdict-presence",
            "blocker-closure", "branch"}

with open(sys.argv[1]) as f:
    m = yaml.safe_load(f)

gates = m.get("gate_prerequisites", []) or []
present = {g.get("category") for g in gates}

missing = required - present
unknown = present - required - {None}

rc = 0
if missing:
    print(f"verify-gate-categories: missing categories: {sorted(missing)}",
          file=sys.stderr)
    rc = 1
if unknown:
    print(f"verify-gate-categories: unknown categories: {sorted(unknown)}",
          file=sys.stderr)
    rc = 1

if rc == 0:
    print("verify-gate-categories: OK (all six categories covered)")
sys.exit(rc)
PY
