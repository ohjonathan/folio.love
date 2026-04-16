#!/usr/bin/env bash
# verify-schema.sh — validate both example manifests against
# manifest/deliverable-manifest.schema.yaml:
#   1. example-manifest.yaml (v1.0.0 shape; backward-compat guard)
#   2. example-user-facing-manifest.yaml (v1.1 shape; user_facing + pre_a)
#
# Dependency: `check-jsonschema` (https://check-jsonschema.readthedocs.io/).
# Install:    pip install check-jsonschema   (or: pipx install check-jsonschema)
#
# Exits 0 on success, non-zero on schema failure or missing dependency.

set -euo pipefail

here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
bundle="$(cd "$here/.." && pwd)"

schema="$bundle/manifest/deliverable-manifest.schema.yaml"
manifests=(
  "$bundle/manifest/example-manifest.yaml"
  "$bundle/manifest/example-user-facing-manifest.yaml"
)

if ! command -v check-jsonschema >/dev/null 2>&1; then
  echo "verify-schema: FAILED — check-jsonschema is not installed." >&2
  echo "verify-schema: this check is required (v1.1.1). Silent-skip was removed" >&2
  echo "verify-schema: because an absent validator looks identical to a passing one." >&2
  echo "install:  pip install check-jsonschema   (or pipx install check-jsonschema)" >&2
  exit 1
fi

for manifest in "${manifests[@]}"; do
  echo "verify-schema: validating $manifest against $schema"
  check-jsonschema --schemafile "$schema" "$manifest"
done
echo "verify-schema: OK (${#manifests[@]} manifests validated)"
