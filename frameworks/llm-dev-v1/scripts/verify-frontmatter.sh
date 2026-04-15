#!/usr/bin/env bash
# verify-frontmatter.sh — every template's `required_tokens` +
# `optional_tokens` frontmatter entries match the <TOKEN> references in
# the body.
#
# - Any token used in body but missing from frontmatter -> failure.
# - Any token declared in frontmatter but not referenced in body -> failure.
#
# Exits 0 on success, non-zero with a per-template report otherwise.

set -euo pipefail

here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
bundle="$(cd "$here/.." && pwd)"
templates_dir="$bundle/templates"

rc=0
tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT

for tpl in "$templates_dir"/*.md; do
  name="$(basename "$tpl")"

  # Extract frontmatter (between leading `---` lines).
  awk '/^---$/{c++; next} c==1 {print}' "$tpl" > "$tmp/fm"

  # Extract declared tokens from required_tokens and optional_tokens lists.
  # Tolerates `  - TOKEN_NAME` indentation.
  awk '
    /^required_tokens:/ { mode="req"; next }
    /^optional_tokens:/ { mode="opt"; next }
    /^[a-z_]+:/         { mode=""; next }
    mode!="" && /^[[:space:]]+-[[:space:]]+/ {
      sub(/^[[:space:]]+-[[:space:]]+/, "")
      print
    }
  ' "$tmp/fm" | sort -u > "$tmp/declared"

  # Extract body tokens (everything after the second ---). Use >=2 so
  # subsequent horizontal rules inside the body don't stop extraction.
  awk 'flag>=2{print} /^---$/{flag++}' "$tpl" \
    | grep -oE '<[A-Z][A-Z0-9_]+(\[\])?\??>' \
    | sed -E 's/\[\]|\?|<|>//g' \
    | sort -u > "$tmp/used"

  # Allowed exemption: <FINAL_REPORT_SCHEMA> is template-local schema.
  sed -i.bak '/^FINAL_REPORT_SCHEMA$/d' "$tmp/used" 2>/dev/null || true

  missing=$(comm -23 "$tmp/used" "$tmp/declared")
  extra=$(comm -13 "$tmp/used" "$tmp/declared")

  if [[ -n "$missing" || -n "$extra" ]]; then
    rc=1
    echo "verify-frontmatter: $name" >&2
    [[ -n "$missing" ]] && echo "  used but NOT in frontmatter: $missing" >&2
    [[ -n "$extra"   ]] && echo "  declared but NOT used in body: $extra" >&2
  fi
done

if [[ $rc -eq 0 ]]; then
  echo "verify-frontmatter: OK (frontmatter ⇔ body for all templates)"
fi
exit $rc
