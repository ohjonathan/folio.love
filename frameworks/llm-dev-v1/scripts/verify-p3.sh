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
# v1.2 adversarial-family invariant: under manifest_version ≥ 1.2.0,
# the adversarial family at B.1 / B.2 / D.2 must not share a provider
# with the author family (provider = first hyphen-delimited segment of
# the family name). Same-provider adversarial is advisory-only and
# requires a structured `cross_provider_adversarial_passes[]` entry
# whose provider differs from the author's AND whose artifact_path is
# referenced by a `gate_prerequisites` entry of category
# verdict-presence. Pre-v1.2 manifests are grandfathered.
#
# Dependency: `python3` with pyyaml.
#
# Exits 0 on success, non-zero with diagnostics otherwise.

set -euo pipefail

here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
bundle="$(cd "$here/.." && pwd)"

# v1.2: accept `--manifest <path>` to validate a single adopter manifest.
# Default (no args): validate the two bundled example manifests.
if [[ "${1:-}" == "--manifest" ]]; then
  if [[ -z "${2:-}" || ! -r "$2" ]]; then
    echo "usage: verify-p3.sh [--manifest <path>]" >&2
    exit 1
  fi
  manifests=("$2")
else
  manifests=(
    "$bundle/manifest/example-manifest.yaml"
    "$bundle/manifest/example-user-facing-manifest.yaml"
  )
fi

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

    # v1.2 adversarial-family provider invariant (grandfathered for < 1.2.0).
    def _version_tuple(v):
        try:
            return tuple(int(x) for x in str(v).split("."))
        except Exception:
            return (0, 0, 0)

    manifest_version = m.get("manifest_version", "1.0.0")
    if _version_tuple(manifest_version) >= (1, 2, 0):
        def _provider_of(family):
            if not family:
                return ""
            return str(family).split("-", 1)[0]

        author_providers = {_provider_of(f) for f in author_families if f}

        # v1.2 escape hatch (structured; replaces the v1.2.0-RC1 gate-id-prefix
        # convention that Codex ALIGN-BLOCKER1 showed was bypassable by a
        # dummy gate prerequisite). The manifest declares
        # `cross_provider_adversarial_passes[]` with
        # {phase, family, provider, artifact_path}; verify-p3 asserts:
        #   1. provider != any author provider (the second pass IS
        #      cross-provider);
        #   2. a `gate_prerequisites` entry of category `verdict-presence`
        #      references `artifact_path` in its `verification.command`
        #      (the second-pass artifact is mechanically checked at D.6).
        # If both conditions hold, the phase is authorized for advisory-only
        # same-provider adversarial.
        xprov_passes = m.get("cross_provider_adversarial_passes") or []
        gate_prereqs = m.get("gate_prerequisites") or []
        escape_phases = set()
        for i, xp in enumerate(xprov_passes):
            xp_phase = xp.get("phase")
            xp_family = xp.get("family")
            xp_provider = xp.get("provider")
            xp_artifact = xp.get("artifact_path")
            ok = True
            # Provider cross-reference: must be different from author providers.
            if xp_provider in author_providers:
                print(
                    f"verify-p3: {path}: cross_provider_adversarial_passes[{i}] "
                    f"provider {xp_provider!r} is the SAME as an author provider "
                    f"{sorted(author_providers)}; the second pass must be cross-"
                    f"provider to act as a v1.2 escape hatch.",
                    file=sys.stderr,
                )
                overall_rc = 1
                ok = False
            # verdict-presence gate cross-reference: some gate_prerequisites entry
            # of category verdict-presence must reference xp_artifact in its
            # verification.command string. This ties the escape hatch to a
            # mechanically-checkable D.6 gate row.
            artifact_referenced = False
            for gp in gate_prereqs:
                if gp.get("category") != "verdict-presence":
                    continue
                cmd = ((gp.get("verification") or {}).get("command") or "")
                if xp_artifact and xp_artifact in cmd:
                    artifact_referenced = True
                    break
            if not artifact_referenced:
                print(
                    f"verify-p3: {path}: cross_provider_adversarial_passes[{i}] "
                    f"artifact_path {xp_artifact!r} is not referenced by any "
                    f"`gate_prerequisites` entry with category=verdict-presence. "
                    f"The escape hatch requires a mechanical D.6 check that the "
                    f"second-pass artifact exists — add a gate_prerequisite whose "
                    f"verification.command contains this artifact_path.",
                    file=sys.stderr,
                )
                overall_rc = 1
                ok = False
            if ok:
                escape_phases.add(xp_phase)

        adv_check_phases = {"B.1", "B.2", "D.2"}
        for entry in assignments:
            phase = entry.get("phase")
            if phase not in adv_check_phases:
                continue
            for fam, role in entry.get("assignments", {}).items():
                if role != "adversarial":
                    continue
                fam_provider = _provider_of(fam)
                if fam_provider in author_providers and phase not in escape_phases:
                    print(
                        f"verify-p3: {path}: phase {phase}: adversarial family "
                        f"{fam!r} shares provider {fam_provider!r} with author "
                        f"{sorted(author_families)!r}. v1.2 adversarial-family "
                        f"invariant (manifest_version {manifest_version}) "
                        f"requires a different provider; same-provider "
                        f"adversarial is advisory-only and must be authorized "
                        f"via a `cross_provider_adversarial_passes[]` entry "
                        f"for phase {phase} with a cross-provider `provider` "
                        f"and an `artifact_path` that a verdict-presence "
                        f"`gate_prerequisites` entry references (see "
                        f"framework.md § P3 Adversarial-family invariant).",
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
