#!/usr/bin/env python3
"""Select 50 unique PPTX decks from sample_powerpoint and symlink into corpus/."""

import os
from pathlib import Path

SAMPLE_DIR = Path(__file__).resolve().parent.parent.parent / "sample_powerpoint"
CORPUS_DIR = Path(__file__).resolve().parent / "corpus"

CORPUS_DIR.mkdir(parents=True, exist_ok=True)

# Collect all non-copy PPTX files, skip .potx template
candidates = sorted([
    f for f in SAMPLE_DIR.iterdir()
    if f.suffix == ".pptx" and " copy" not in f.name
])

print(f"Found {len(candidates)} candidate PPTX files (non-copy)")

# Select first 50
selected = candidates[:50]

for existing in CORPUS_DIR.iterdir():
    if existing.is_symlink() or existing.suffix == ".pptx":
        existing.unlink()

for i, src in enumerate(selected, 1):
    dst = CORPUS_DIR / src.name
    dst.symlink_to(src)
    size_mb = src.stat().st_size / (1024 * 1024)
    print(f"  [{i:2d}] {src.name} ({size_mb:.1f} MB)")

print(f"\nCorpus ready: {len(selected)} decks in {CORPUS_DIR}")
