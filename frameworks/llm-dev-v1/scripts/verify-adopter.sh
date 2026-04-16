#!/usr/bin/env bash
# verify-adopter.sh — unified entrypoint for adopters (v1.2+).
#
# Runs the four manifest-scoped conformance checks against a single
# adopter-authored manifest path:
#   - verify-schema.sh      --manifest <path>
#   - verify-p3.sh          --manifest <path>
#   - verify-gate-categories.sh --manifest <path>
#   - verify-artifact-paths.sh --manifest <path>
#
# Reports per-check PASS/FAIL and an aggregate verdict. Intended for
# adopter CI (where only the adopter's own manifest matters) — distinct
# from `verify-all.sh`, which validates the bundle's own example
# manifests plus bundle-level prose (tokens, portability, frontmatter).
#
# Usage: verify-adopter.sh <manifest-path>
#
# Exits 0 on success (all 4 pass), 1 on any failure, 2 on missing dep
# or unreadable manifest.

set -uo pipefail

if [[ $# -lt 1 ]]; then
  echo "usage: verify-adopter.sh <manifest-path>" >&2
  exit 1
fi

manifest="$1"
if [[ ! -r "$manifest" ]]; then
  echo "verify-adopter: cannot read $manifest" >&2
  exit 2
fi

here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

checks=(
  "verify-schema.sh"
  "verify-p3.sh"
  "verify-gate-categories.sh"
  "verify-artifact-paths.sh"
)

failed=()
skipped=()

echo "verify-adopter: validating $manifest against 4 checks"
echo

for c in "${checks[@]}"; do
  echo "::: $c --manifest <manifest> :::"
  if bash "$here/$c" --manifest "$manifest"; then
    :
  else
    status=$?
    if [[ $status -eq 2 ]]; then
      skipped+=("$c")
    else
      failed+=("$c")
    fi
  fi
  echo
done

echo "-----------------------------------------------------------------"
if [[ ${#failed[@]} -gt 0 ]]; then
  echo "verify-adopter: FAILED: ${failed[*]}"
  exit 1
elif [[ ${#skipped[@]} -gt 0 ]]; then
  echo "verify-adopter: PASSED (skipped: ${skipped[*]}; ${#checks[@]} total checks)"
  exit 0
else
  echo "verify-adopter: PASSED (${#checks[@]}/${#checks[@]} checks against $manifest)"
  exit 0
fi
