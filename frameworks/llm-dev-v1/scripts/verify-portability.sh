#!/usr/bin/env bash
# verify-portability.sh — template bodies contain no host-project strings.
#
# Host-project strings are anything that assumes the framework's origin
# repo. The grep excludes:
#   - HTML provenance comments (`<!-- Provenance: ... -->`)
#   - `review-board/` and `docs/` non-normative files (see PROVENANCE.md)
#   - Example fills in tokens.md (documented in its "Example fill" column)
#   - Commentary in the manifest example YAML header
#
# Exits 0 on success, non-zero with the offending lines otherwise.

set -euo pipefail

here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
bundle="$(cd "$here/.." && pwd)"

# Normative paths we scan.
scan_paths=(
  "$bundle/framework.md"
  "$bundle/playbook.md"
  "$bundle/README.md"
  "$bundle/ROADMAP.md"
  "$bundle/CHANGELOG.md"
  "$bundle/PROVENANCE.md"
  "$bundle/templates"
  "$bundle/manifest/generator-spec.md"
  "$bundle/manifest/deliverable-manifest.schema.yaml"
  "$bundle/examples"
)

# Patterns that indicate a host-project leak.
host_patterns='(johnny-os|Ontos_Context_Map|phase-1/deliverable|\bD[12]\b(?!\s*(section|review|report|pattern|comment)))'

# First pass: raw grep.
tmp="$(mktemp)"
trap 'rm -f "$tmp"' EXIT

grep -rnE 'johnny-os|Ontos_Context_Map|phase-1/deliverable' "${scan_paths[@]}" > "$tmp" || true

# Filter out allowed exemptions line-by-line.
filtered="$(awk '
  # Provenance HTML comments.
  /<!-- Provenance/ { next }
  # PROVENANCE.md itself intentionally documents provenance.
  /PROVENANCE\.md/  { next }
  { print }
' "$tmp")"

if [[ -n "$filtered" ]]; then
  echo "verify-portability: host-project strings detected in normative files:" >&2
  echo "$filtered" >&2
  exit 1
fi

echo "verify-portability: OK (no host-project strings in normative files)"
