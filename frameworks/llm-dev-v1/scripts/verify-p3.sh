#!/usr/bin/env bash
# verify-p3.sh — confirm each example manifest's `model_assignments`
# satisfies the strict P3 rule:
#   - Phases B.1, D.2, D.5 each have ≥3 distinct non-author families
#     (across all entries for that phase, aggregated).
#   - No family holds two roles in the same assignments map (per-entry
#     check; same family across separate entries is allowed as
#     same-family-separate-session per P10).
#   - Author family (inferred from phase-A spec-author role) never
#     appears as a reviewer on the same phase.
#
# v1.1 user-facing extension: when `user_facing: true`, additionally
# assert that at least one entry for each of B.1, B.2, D.2 has a
# `product` role in its assignments. The Product family may overlap
# an engineering family from another entry on the same phase, provided
# the Product assignment lives in its own list entry.
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
from collections import defaultdict

paths = sys.argv[1:]
overall_rc = 0

for path in paths:
    with open(path) as f:
        m = yaml.safe_load(f)

    assignments = m.get("model_assignments", [])
    user_facing = bool(m.get("user_facing", False))

    # Author family(ies) from phase A spec-author role.
    author_families = set()
    for entry in assignments:
        if entry.get("phase") == "A":
            for fam, role in entry.get("assignments", {}).items():
                if role == "spec-author":
                    author_families.add(fam)

    # Aggregate by phase: all family → role mappings across entries.
    # phase_families[phase]      -> set of distinct families across all entries.
    # phase_roles[phase]         -> set of roles across all entries.
    # phase_family_roles[(p, f)] -> list of all roles family f holds on phase p
    #                               across every entry (preserves duplicates).
    phase_families = defaultdict(set)
    phase_roles = defaultdict(set)
    phase_family_roles = defaultdict(list)
    for entry in assignments:
        phase = entry.get("phase")
        amap = entry.get("assignments", {})
        phase_families[phase].update(amap.keys())
        phase_roles[phase].update(amap.values())
        # P10 per-entry: no family appears twice in one assignments map.
        fams_in_entry = list(amap.keys())
        if len(fams_in_entry) != len(set(fams_in_entry)):
            print(f"verify-p3: {path}: phase {phase}: duplicate family in one assignments map (P10 per-session)", file=sys.stderr)
            overall_rc = 1
        for fam, role in amap.items():
            phase_family_roles[(phase, fam)].append(role)

    # P3 per-(phase, family) cross-entry check: a family may hold AT MOST ONE
    # non-Product role per phase. The v1.1 user-facing extension allows a
    # Product role to overlap an engineering role IF dispatched in a separate
    # P10 session (separate model_assignments entry); no other overlaps are
    # allowed. Without this aggregation check, a manifest can split
    # `codex: peer` and `codex: adversarial` into two B.1 entries and pass
    # the per-entry P10 guard while still violating P3.
    for (phase, fam), roles in phase_family_roles.items():
        non_product_roles = [r for r in roles if r != "product"]
        if len(non_product_roles) > 1:
            print(
                f"verify-p3: {path}: phase {phase}: family {fam!r} holds "
                f"{len(non_product_roles)} non-Product roles "
                f"({sorted(non_product_roles)}) across model_assignments "
                f"entries. P3: a family may hold at most one role per phase. "
                f"v1.1 user-facing extension only allows Product (in a "
                f"separate P10 session) to overlap an engineering role; "
                f"multiple non-Product roles for one family on one phase "
                f"is a P3 violation regardless of session count.",
                file=sys.stderr,
            )
            overall_rc = 1

    # v1.0 mandatory review phases (always require ≥3 non-author engineering families).
    # v1.1 adds B.2 to this set when a manifest declares B.2 in model_assignments
    # (B.2 is a review-board phase by playbook §B; v1.0 example happened not to use it).
    # Generator-spec invariant 4 (rev v1.1) names B.1 + B.2 (when declared) + D.2 + D.5.
    review_phases = {"B.1", "D.2", "D.5"}
    if "B.2" in phase_families:
        review_phases = review_phases | {"B.2"}
    for phase in review_phases:
        fams = phase_families.get(phase, set())
        # Engineering-family count: subtract `product` role entries (Product
        # may overlap an engineering family per the v1.1 user-facing extension;
        # the engineering ≥3 floor must be satisfied independently of Product).
        engineering_fams = set()
        for entry in assignments:
            if entry.get("phase") != phase:
                continue
            for fam, role in entry.get("assignments", {}).items():
                if role != "product":
                    engineering_fams.add(fam)
        non_author = engineering_fams - author_families
        if len(non_author) < 3:
            print(
                f"verify-p3: {path}: phase {phase}: {len(non_author)} non-author "
                f"engineering family assignments across all entries (need ≥3; "
                f"Product role doesn't count toward the engineering floor). "
                f"Found engineering families: {sorted(non_author)}; author: "
                f"{sorted(author_families)}",
                file=sys.stderr,
            )
            overall_rc = 1
        overlap = fams & author_families
        if overlap:
            print(
                f"verify-p3: {path}: phase {phase}: author family(ies) {sorted(overlap)} "
                f"also review — P3 violation",
                file=sys.stderr,
            )
            overall_rc = 1

    if user_facing:
        # Presence: artifacts.product_verdict must be declared and non-empty
        # (template 06's 4-row intake reads this path verbatim; absence
        # causes a runtime halt at meta-consolidation).
        artifacts = m.get("artifacts", {}) or {}
        pv = artifacts.get("product_verdict")
        if not pv or not isinstance(pv, str) or not pv.strip():
            print(
                f"verify-p3: {path}: user_facing=true but "
                f"artifacts.product_verdict is missing or empty (v1.1 P3 "
                f"extension + generator-spec invariant 15 require a non-empty "
                f"product_verdict path when user_facing: true)",
                file=sys.stderr,
            )
            overall_rc = 1

        # Per-phase role + singular-product checks.
        user_facing_phases = {"B.1", "B.2", "D.2"}
        # Count `product` role occurrences per phase across all entries.
        phase_product_count = defaultdict(int)
        for entry in assignments:
            p = entry.get("phase")
            for role in entry.get("assignments", {}).values():
                if role == "product":
                    phase_product_count[p] += 1
        for phase in user_facing_phases:
            roles = phase_roles.get(phase, set())
            if "product" not in roles:
                print(
                    f"verify-p3: {path}: user_facing=true but phase {phase} has no "
                    f"`product` role in any model_assignments entry (v1.1 P3 "
                    f"extension requires Product reviewer on B.1/B.2/D.2 when "
                    f"user_facing: true)",
                    file=sys.stderr,
                )
                overall_rc = 1
            if phase_product_count.get(phase, 0) > 1:
                print(
                    f"verify-p3: {path}: phase {phase} has "
                    f"{phase_product_count[phase]} `product` role entries; "
                    f"v1.1 singular-product policy (generator-spec invariant "
                    f"15c) allows at most one Product reviewer per phase "
                    f"because template 06's 4-row intake reads a single "
                    f"<PRODUCT_VERDICT_PATH>. Either remove the extra entry, "
                    f"or upgrade template 06 intake to a list first.",
                    file=sys.stderr,
                )
                overall_rc = 1

if overall_rc == 0:
    suffix = f" (user-facing extension checked on {sum(1 for p in paths if yaml.safe_load(open(p)).get('user_facing', False))} of {len(paths)} manifests)"
    print(f"verify-p3: OK — all manifests satisfy strict P3{suffix}")
sys.exit(overall_rc)
PY
