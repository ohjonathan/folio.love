#!/usr/bin/env bash
# verify-tokens.sh — every <ANGLE_UPPER> token used in any template body
# is defined in tokens.md (and vice versa, modulo the allowed
# <FINAL_REPORT_SCHEMA> placeholder).
#
# Exits 0 on success, non-zero with a list of offending tokens otherwise.

set -euo pipefail

here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
bundle="$(cd "$here/.." && pwd)"

templates_dir="$bundle/templates"
framework="$bundle/framework.md"
playbook="$bundle/playbook.md"
generator_spec="$bundle/manifest/generator-spec.md"
tokens="$bundle/tokens.md"

tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT

# Tokens actually used in template bodies (+ framework / playbook /
# generator-spec). Strip frontmatter optional/required markers and
# list-form brackets; normalize to <NAME>.
grep -rhoE '<[A-Z][A-Z0-9_]+(\[\])?\??>' \
     "$templates_dir" "$framework" "$playbook" "$generator_spec" \
  | sed -E 's/\[\]|\?//g' \
  | sort -u > "$tmp/used"

# Tokens declared in tokens.md (Category tables use `<TOKEN>` / `<TOKEN?>` /
# `<TOKEN:LIST>` / `<TOKEN[]>`). Two passes so :LIST and [] forms both
# normalize to the bare `<TOKEN>` form.
grep -oE '<[A-Z][A-Z0-9_]+(:LIST|\[\])?\??>' "$tokens" \
  | sed -E 's/:LIST|\[\]|\?//g' \
  | sort -u > "$tmp/defined"

# Add the explicit exemption: <FINAL_REPORT_SCHEMA> is a template-local
# schema placeholder, intentionally not defined in tokens.md.
echo "<FINAL_REPORT_SCHEMA>" >> "$tmp/defined"
sort -u "$tmp/defined" -o "$tmp/defined"

# Orchestrator-only tokens (v1.1.1): tokens consumed outside template bodies
# (manifest generator, orchestrator runbook, CHANGELOG/PR tooling). They are
# legitimately defined in tokens.md but never appear in <ANGLE_UPPER> form in
# any template. Extract them from the "Orchestrator-only tokens" section of
# tokens.md and skip the defined-but-not-used warning for them.
#
# Flag-based awk range so the next `## ` heading terminates extraction
# regardless of its first letter (an earlier range `/,/^## [^O]/` broke on
# sections starting with 'O' — ADV-SF-001).
awk '
  /^## Orchestrator-only tokens/ { flag = 1; next }
  flag && /^## / { flag = 0 }
  flag
' "$tokens" \
  | grep -oE '<[A-Z][A-Z0-9_]+>' \
  | sort -u > "$tmp/orchestrator_only"

used_not_defined=$(comm -23 "$tmp/used" "$tmp/defined")
defined_not_used_raw=$(comm -13 "$tmp/used" "$tmp/defined")
if [[ -s "$tmp/orchestrator_only" ]]; then
  defined_not_used=$(echo "$defined_not_used_raw" | grep -vFx -f "$tmp/orchestrator_only" || true)
else
  defined_not_used="$defined_not_used_raw"
fi

rc=0

if [[ -n "$used_not_defined" ]]; then
  echo "verify-tokens: tokens used but NOT defined in tokens.md:" >&2
  printf '  %s\n' $used_not_defined >&2
  rc=1
fi

# Pseudo-token scan (generator-spec.md invariant 13). Computed forms
# such as <PHASE_ID+1>, <N*2>, <X/Y>, <PHASE_A-PHASE_B> must never
# appear in any template body.
#
# Scope: only <UPPER_TOKEN><operator><UPPER_OR_DIGIT> shapes are
# flagged. Lowercase placeholders (<free-form>, <phase>) and HTML
# comments are not pseudo-tokens. The `-` is placed LAST in the
# character class so it is treated as a literal hyphen, not a range.
pseudo_hits=$(grep -rnE '<[A-Z][A-Z0-9_]*[+*/-][A-Z0-9_]+>' "$templates_dir" \
              "$framework" "$playbook" "$generator_spec" 2>/dev/null \
  | grep -vE '<!--' \
  || true)
if [[ -n "$pseudo_hits" ]]; then
  echo "verify-tokens: computed pseudo-token forms detected (invariant 13):" >&2
  echo "$pseudo_hits" >&2
  rc=1
fi

if [[ -n "$defined_not_used" ]]; then
  # Defined-but-unused is a warning, not a failure — some tokens are
  # reserved for future templates. Print them but do not fail.
  echo "verify-tokens: [warn] tokens defined but not referenced:" >&2
  printf '  %s\n' $defined_not_used >&2
fi

if [[ $rc -eq 0 ]]; then
  echo "verify-tokens: OK (all template tokens are defined)"
fi
exit $rc
