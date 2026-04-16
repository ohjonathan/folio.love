#!/usr/bin/env bash
# day-one.sh — v1.2+ adopter bootstrap.
#
# Creates an initial manifest + tracker skeleton for a new deliverable
# and seeds tokens.local.md if absent. Non-destructive: exits if any
# target file already exists.
#
# Usage: bash ops/llm-dev-v1/examples/day-one.sh <deliverable-id>
#
# Environment overrides:
#   MANIFEST_DIR  — where manifests live. Default: <adopter-repo-root>/manifests/
#                   Convention: `frameworks/manifests/` for monorepos that host
#                   the bundle alongside manifests; `manifests/` for standalone
#                   adopter repos.
#
# Assumes $PWD is the adopter-repo-root; exits with a helpful message if
# the script's bundle location is ambiguous.

set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "usage: bash ops/llm-dev-v1/examples/day-one.sh <deliverable-id>" >&2
  echo "(run from your adopter-repo-root)" >&2
  exit 1
fi

deliverable_id="$1"

# Validate deliverable-id shape: must match the v1.2 manifest.id regex
# (lowercase start, lowercase/digits/dash/dot components).
if ! [[ "$deliverable_id" =~ ^[a-z][a-z0-9]*([.-][a-z0-9]+)*$ ]]; then
  echo "day-one: invalid deliverable-id '$deliverable_id'" >&2
  echo "day-one: must match ^[a-z][a-z0-9]*([.-][a-z0-9]+)*\$ (schema.id pattern)" >&2
  echo "day-one: e.g., 'currency-converter' or 'my-thing-v0.6.4'" >&2
  exit 1
fi

here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
bundle="$(cd "$here/.." && pwd)"
adopter_repo_root="${PWD}"

# Default MANIFEST_DIR: adopter-repo-root/manifests/. Adopter can override.
manifest_dir="${MANIFEST_DIR:-$adopter_repo_root/manifests}"
mkdir -p "$manifest_dir"

tracker_dir="$adopter_repo_root/docs/trackers"
mkdir -p "$tracker_dir"

# 1. Create manifest skeleton from the bundled example.
src="$bundle/manifest/example-manifest.yaml"
dst="$manifest_dir/$deliverable_id.yaml"
if [[ -e "$dst" ]]; then
  echo "day-one: manifest already exists at $dst (not overwriting)" >&2
  exit 1
fi
sed -E \
    -e "s/^id: currency-converter$/id: $deliverable_id/" \
    -e "s/^slug: currency-converter$/slug: $deliverable_id/" \
    "$src" > "$dst"
echo "day-one: created manifest skeleton at $dst"

# 2. Create tracker skeleton.
tracker="$tracker_dir/$deliverable_id.md"
if [[ ! -e "$tracker" ]]; then
  cat > "$tracker" <<TRACKER
# $deliverable_id — Tracker

| Phase | Owner | Status | Artifact | Evidence | Timestamp |
|-------|-------|--------|----------|----------|-----------|
| 0     |       | pending |          |          |           |
TRACKER
  echo "day-one: created tracker skeleton at $tracker"
else
  echo "day-one: tracker already exists at $tracker (skipping)"
fi

# 3. Seed tokens.local.md inside the bundle copy (git-ignore recommended).
tokens_local="$bundle/tokens.local.md"
if [[ ! -e "$tokens_local" ]]; then
  cp "$bundle/tokens.md" "$tokens_local"
  echo "day-one: seeded $tokens_local (fill it before dispatch)"
else
  echo "day-one: tokens.local.md already present at $tokens_local (skipping)"
fi

cat <<NEXT

day-one: bootstrap complete.

Next steps:
  1. Edit $dst to match this deliverable's scope (allowed_paths,
     forbidden_paths, gate_prerequisites, model_assignments, etc.).
  2. Fill $tokens_local with your adopter values (CLI invocations,
     workspace path, test command, MANIFEST_DIR, CLI_CODEX_MODEL).
  3. Preflight: bash $bundle/scripts/verify-tokens.sh --probe-codex-model <CLI_CODEX_MODEL>
  4. Validate the manifest: bash $bundle/scripts/verify-adopter.sh "$dst"
  5. See $bundle/README.md § Adopter onboarding (v1.2+) for the full flow.
NEXT
