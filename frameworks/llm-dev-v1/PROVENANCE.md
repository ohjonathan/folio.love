# Provenance

This bundle contains two categories of files:

1. **Normative** — the framework's shipping contract. Adopters copy these
   into their repos and depend on their stability across versions.
2. **Non-normative provenance** — historical artifacts kept in-tree for
   transparency. Adopters do **not** need to carry them; they can be
   deleted from a downstream copy without affecting the framework's
   behavior.

## Normative files

Everything in the bundle EXCEPT the paths listed in the next section:

- `framework.md`, `playbook.md`, `README.md`, `ROADMAP.md`, `CHANGELOG.md`,
  `tokens.md`, `PROVENANCE.md`, `LICENSE`, `.gitignore`
- `templates/*.md`
- `manifest/*.yaml`, `manifest/generator-spec.md`
- `examples/*.md`
- `scripts/*.sh`

Breaking changes to any normative file bump the bundle major version.

## Non-normative provenance files

These capture how v1.0.0 and v1.1.0 were built and reviewed. They are
useful for understanding framework decisions but are not part of the
contract.

| Path                              | What it is                                                                 |
|-----------------------------------|----------------------------------------------------------------------------|
| `docs/v1-build-plan.md`          | The internal build plan approved before v1.0.0 drafting began.              |
| `docs/v1.1-build-plan.md`        | The v1.1 build plan drafted at end of the v1.0.0 release session.           |
| `docs/v1.1-doctrine-decisions.md`| Annex capturing four doctrine resolutions that shaped v1.1 execution.       |
| `review-board/v1.0.0-spec-verdict.md` | Canonical review verdict that triggered the v1.0.0 revision cycle.       |
| `review-board/v1.0.0-review-*.md` | Family verdicts (Claude, Codex, Gemini teams) that fed the canonical verdict. |
| `review-board/_baselines/*.md`   | Baseline comparisons for the review itself.                                 |
| `review-board/v1.0.0-spec-verdict-response.md` | The fix-summary response addressing every blocker (added in the v1.0.0 revision). |
| `review-board/v1.0.0-rereview-dispatch.md` | The focused re-review dispatch run after the v1.0.0 revision.         |
| `review-board/v1.0.0-rereview-*.md` | v1.0.0 re-review family verdicts and consolidated re-review verdict.       |
| `review-board/v1.1.0-*`          | v1.1.0 review-board artifacts (canonical verdict, family verdicts, response doc). Produced during Phase 7 of the v1.1 build plan. |

**What a downstream adopter does with these.**

- **Keep them if** the adopter wants an audit trail of framework
  decisions, e.g., for a security review or a regulated environment.
- **Delete them if** the adopter wants the minimum bundle. No template
  references them; removing the `docs/` and `review-board/` directories
  does not change any template's behavior.

**What the framework maintainer does with these.**

- Keeps them as part of the repo history.
- Adds new entries (per-minor-version review verdicts, retrospectives)
  as the framework evolves. These land under `review-board/` with a
  version prefix so they are mechanically distinguishable from
  downstream review artifacts produced by deliverables using the
  framework.

## License

v1.1 ships the bundle under Apache License 2.0. The canonical text is
at `LICENSE` (bundle root); see also `README.md` § License.

Apache 2.0 was chosen for maximum compatibility with downstream projects
(permissive, patent-grant clause, compatible with common commercial and
open-source licenses). Adopters copying this bundle into their repos
inherit the license and must include `LICENSE` in the downstream copy.
If the downstream project is under a different license, Apache 2.0's
permissive terms allow the bundle to be redistributed as-is or
relicensed per Apache 2.0 §4.

`LICENSE` is normative: changing the license text is a breaking change
and bumps the bundle major.
