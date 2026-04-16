#!/usr/bin/env bash
# verify-all.sh — run the full conformance suite. Exits non-zero if any
# check fails. As of v1.1.1, schema validation hard-fails when
# check-jsonschema is absent (it used to soft-skip; silent-skip on a
# missing validator looked identical to a passing check). Any other
# check that signals exit-2 is still treated as "skipped (not failed)"
# so CI can surface missing optional dependencies without tripping the
# overall gate.

set -u

here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
bundle="$(cd "$here/.." && pwd)"

checks=(
  "verify-schema.sh"
  "verify-tokens.sh"
  "verify-frontmatter.sh"
  "verify-p3.sh"
  "verify-pre-a.sh"
  "verify-gate-categories.sh"
  "verify-artifact-paths.sh"
  "verify-portability.sh"
  "verify-circuit-breaker.sh"
)

failed=()
skipped=()

for c in "${checks[@]}"; do
  echo "::: $c :::"
  if bash "$here/$c"; then
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

# v1.2 fixture regression: verify-d6-gate.sh runs per-deliverable, not
# per-bundle, so the bundle check validates the script against a known-good
# fixture (examples/d6-gate-fixture.md). If the parser or schema drifts,
# this fires before any adopter's deliverable run does.
echo "::: verify-d6-gate.sh (fixture) :::"
if bash "$here/verify-d6-gate.sh" "$bundle/examples/d6-gate-fixture.md"; then
  :
else
  status=$?
  if [[ $status -eq 2 ]]; then
    skipped+=("verify-d6-gate.sh(fixture)")
  else
    failed+=("verify-d6-gate.sh(fixture)")
  fi
fi
echo

echo "-----------------------------------------------------------------"
if [[ ${#failed[@]} -gt 0 ]]; then
  echo "verify-all: FAILED: ${failed[*]}"
  exit 1
elif [[ ${#skipped[@]} -gt 0 ]]; then
  echo "verify-all: PASSED (skipped: ${skipped[*]})"
  exit 0
else
  echo "verify-all: PASSED"
  exit 0
fi
