#!/usr/bin/env bash
# verify-artifact-paths.sh — enforce placeholder-shape invariants for
# artifact path fields across every example manifest.
#
# Invariants (generator-spec.md 10, 11, 15):
#   - artifacts.canonical_verdict MUST contain <phase> AND must NOT
#     contain <family> or <role>.
#   - artifacts.family_verdict     MUST contain <phase> AND <family> AND
#     <role>.
#   - artifacts.verification       MUST contain <family>.
#   - artifacts.product_verdict (v1.1, when present) MUST contain
#     <phase> AND <family>; must NOT contain <role>. The Product lens
#     is always per-family and phase-scoped; role is fixed to "product"
#     in template 19's output schema and does not belong in the path.
#
# These invariants catch JSON-Schema-shaped "type: string" approvals of
# wrong-shape paths that the generator or downstream consumers would
# fail on.
#
# Dependency: python3 + pyyaml.

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
failures = []  # list of diagnostic strings; any entry = overall failure.

def require(needle, where, field, manifest_path):
    if needle not in where:
        failures.append(
            f"verify-artifact-paths: {manifest_path}: artifacts.{field} "
            f"missing required placeholder '{needle}': {where!r}"
        )

def forbid(needle, where, field, manifest_path):
    if needle in where:
        failures.append(
            f"verify-artifact-paths: {manifest_path}: artifacts.{field} "
            f"must NOT contain '{needle}': {where!r}"
        )

for path in paths:
    with open(path) as f:
        m = yaml.safe_load(f)

    artifacts = m.get("artifacts", {}) or {}
    canonical = artifacts.get("canonical_verdict", "")
    family    = artifacts.get("family_verdict", "")
    verify    = artifacts.get("verification", "")
    product   = artifacts.get("product_verdict", "")

    # canonical_verdict: <phase> required; <family>, <role> forbidden.
    require("<phase>",  canonical, "canonical_verdict", path)
    forbid ("<family>", canonical, "canonical_verdict", path)
    forbid ("<role>",   canonical, "canonical_verdict", path)

    # family_verdict: <phase>, <family>, <role> all required.
    require("<phase>",  family, "family_verdict", path)
    require("<family>", family, "family_verdict", path)
    require("<role>",   family, "family_verdict", path)

    # verification: <family> required.
    require("<family>", verify, "verification", path)

    # product_verdict (v1.1): when present, <phase> + <family> required;
    # <role> forbidden. An empty string counts as "not present" and is
    # accepted; if the manifest declares product_verdict at all, it must
    # be shaped correctly. (Presence-when-user_facing is enforced by
    # verify-p3.sh, not here — this script is strictly about placeholder
    # shape.)
    if product:
        require("<phase>",  product, "product_verdict", path)
        require("<family>", product, "product_verdict", path)
        forbid ("<role>",   product, "product_verdict", path)

for diag in failures:
    print(diag, file=sys.stderr)

if failures:
    sys.exit(1)

print(
    f"verify-artifact-paths: OK "
    f"(canonical_verdict / family_verdict / verification / product_verdict "
    f"placeholders valid across {len(paths)} manifests)"
)
PY
