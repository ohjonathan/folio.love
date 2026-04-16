#!/usr/bin/env bash
# verify-d6-gate.sh — parse a D.6 final-approval gate artifact and
# assert every row in its Gate table is PASSED with an allowed
# evidence-class tag (v1.2+ schema).
#
# This is the script-driven D.6 gate described in:
#   - templates/07-final-approval-gate.md (artifact schema)
#   - playbook.md § "D.6 Final-approval gate (v1.2+)"
#
# Allowed evidence classes: test-pass, file-exists, grep-empty,
# grep-match, count-eq, count-gte, command-exit-0,
# command-exit-nonzero, orchestrator-preflight.
# Disallowed: static-inspection, not-run, or anything else.
#
# Usage: verify-d6-gate.sh <final-approval-path>
#
# Exits 0 on success, 1 with row-level diagnostics on failure.
# Exit 2 if python3 missing or the argument is unreadable.

set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "usage: verify-d6-gate.sh <final-approval-path>" >&2
  exit 1
fi

target="$1"

if [[ ! -r "$target" ]]; then
  echo "verify-d6-gate: cannot read $target" >&2
  exit 2
fi

if ! command -v python3 >/dev/null 2>&1; then
  echo "verify-d6-gate: python3 is required" >&2
  exit 2
fi

python3 - "$target" <<'PY'
import re
import sys

path = sys.argv[1]

ALLOWED_CLASSES = {
    "test-pass",
    "file-exists",
    "grep-empty",
    "grep-match",
    "count-eq",
    "count-gte",
    "command-exit-0",
    "command-exit-nonzero",
    "orchestrator-preflight",
}

with open(path, "r") as f:
    lines = f.readlines()

# Locate the Gate table under `## Gate table`.
in_table_section = False
header_seen = False
separator_seen = False
rows = []
row_line_numbers = []

for i, line in enumerate(lines, start=1):
    stripped = line.strip()
    if not in_table_section:
        if stripped.lower().startswith("## gate table"):
            in_table_section = True
        continue
    # We're inside the Gate table section.
    if stripped.startswith("## "):
        # Next section — stop.
        break
    if not stripped:
        # Blank line inside the section — ignore (allows spacing above/below table).
        continue
    if not stripped.startswith("|"):
        # Prose inside the section before or after the table — ignore.
        continue
    # Pipe-delimited line.
    cells = [c.strip() for c in stripped.strip("|").split("|")]
    if not header_seen:
        # Header row: expect at least 5 columns including Result + Evidence class.
        header_seen = True
        expected_cols = {"#", "prerequisite", "result", "evidence class", "reproduction"}
        got_cols = {c.lower() for c in cells}
        missing = expected_cols - got_cols
        if missing:
            print(
                f"verify-d6-gate: {path}: gate table header missing expected "
                f"columns {sorted(missing)}. Got: {cells}",
                file=sys.stderr,
            )
            sys.exit(1)
        # Preserve the column index for Result and Evidence class.
        col_idx = {c.lower(): idx for idx, c in enumerate(cells)}
        continue
    if not separator_seen:
        # Separator row: cells like `---`, `-----`, etc.
        if all(set(c) <= {"-", ":"} and c for c in cells if c):
            separator_seen = True
            continue
        else:
            print(
                f"verify-d6-gate: {path}: expected separator row after header, "
                f"got data row {cells}",
                file=sys.stderr,
            )
            sys.exit(1)
    # Data row.
    if len(cells) < len(col_idx):
        print(
            f"verify-d6-gate: {path}: line {i}: data row has {len(cells)} "
            f"columns, expected ≥{len(col_idx)} ({cells!r})",
            file=sys.stderr,
        )
        sys.exit(1)
    rows.append(cells)
    row_line_numbers.append(i)

if not header_seen:
    print(f"verify-d6-gate: {path}: no Gate table found (looked for '## Gate table')", file=sys.stderr)
    sys.exit(1)

if not rows:
    print(f"verify-d6-gate: {path}: Gate table has a header but no data rows", file=sys.stderr)
    sys.exit(1)

# Validate each row.
failed = 0
for line_no, cells in zip(row_line_numbers, rows):
    row_num = cells[col_idx["#"]]
    prereq = cells[col_idx["prerequisite"]]
    result = cells[col_idx["result"]]
    evclass = cells[col_idx["evidence class"]].strip("`").strip()
    repro = cells[col_idx["reproduction"]]
    if result != "PASSED":
        print(
            f"verify-d6-gate: {path}:{line_no}: row #{row_num} "
            f"({prereq!r}): Result is {result!r}, expected 'PASSED'",
            file=sys.stderr,
        )
        failed += 1
        continue
    if evclass not in ALLOWED_CLASSES:
        print(
            f"verify-d6-gate: {path}:{line_no}: row #{row_num} "
            f"({prereq!r}): Evidence class {evclass!r} not in allowed set "
            f"{sorted(ALLOWED_CLASSES)}",
            file=sys.stderr,
        )
        failed += 1
        continue

if failed:
    print(
        f"verify-d6-gate: FAILED — {failed} row(s) did not satisfy PASSED + "
        f"allowed-evidence-class. See row-level diagnostics above.",
        file=sys.stderr,
    )
    sys.exit(1)

print(f"verify-d6-gate: OK ({len(rows)} rows validated; all PASSED with allowed evidence class)")
sys.exit(0)
PY
