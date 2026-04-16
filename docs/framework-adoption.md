## Framework bundle source

The `frameworks/llm-dev-v1/` directory is a **verbatim copy of the canonical
bundle** maintained in `ohjonathan/johnny-os` at `frameworks/llm-dev-v1/`.

**Do not modify the bundle in this repo.** Any framework bug, friction, or
scope proposal flows upstream:

1. Capture in `docs/retros/llm-dev-v1-adoption.md` as you hit it.
2. File a GitHub issue on `ohjonathan/johnny-os` citing the retro entry.
3. johnny-os ships the fix in a patch or minor release.
4. Resync via `scripts/resync-bundle.sh <path-to-johnny-os> <release-SHA>`.

Folio-local files (manifests, scope-locks, retros, deliverable specs) live
OUTSIDE `frameworks/llm-dev-v1/` — the bundle itself must stay drop-in
replaceable.
