#!/usr/bin/env python3
"""Static checks for the public skill package and corpus-separation boundary."""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "historian-writing" / "SKILL.md"
LOCAL_LINK = re.compile(r"\]\((?!https?://|#)([^)#]+)(?:#[^)]+)?\)")
REQUIRED = [
    ROOT / "README.md",
    ROOT / "docs" / "corpus-boundaries.md",
    ROOT / "docs" / "methodology.md",
    ROOT / "docs" / "roadmap.md",
    ROOT / "historian-writing" / "references" / "ability-library.md",
    ROOT / "historian-writing" / "references" / "evidence-boundaries.md",
    ROOT / "historian-writing" / "references" / "quality-gate.md",
    ROOT / "historian-writing" / "references" / "style-signals.md",
    ROOT / "historian-writing" / "references" / "task-modes.md",
    ROOT / "analysis" / "output" / "corpus_inventory.json",
    ROOT / "analysis" / "output" / "style_profile.json",
    ROOT / "analysis" / "output" / "close_reading_queue.json",
    ROOT / "analysis" / "style-findings.md",
    ROOT / "evals" / "README.md",
]


def fail(message: str) -> None:
    print(f"FAIL: {message}")
    raise SystemExit(1)


def main() -> None:
    for path in REQUIRED:
        if not path.is_file():
            fail(f"missing required file: {path.relative_to(ROOT)}")
    text = SKILL.read_text(encoding="utf-8")
    if not text.startswith("---\nname: historian-writing\n"):
        fail("SKILL.md has no valid historian-writing frontmatter")
    if "disable-model-invocation: true" not in text:
        fail("skill must remain explicitly user-invoked")

    for document in ROOT.rglob("*.md"):
        if ".git" in document.parts:
            continue
        for target in LOCAL_LINK.findall(document.read_text(encoding="utf-8")):
            destination = (document.parent / target).resolve()
            if not destination.exists():
                fail(f"broken local Markdown link in {document.relative_to(ROOT)}: {target}")
            if document.is_relative_to(ROOT / "historian-writing") and not destination.is_relative_to(ROOT / "historian-writing"):
                fail(f"skill package has an external local link: {document.relative_to(ROOT)} -> {target}")

    inventory = json.loads((ROOT / "analysis" / "output" / "corpus_inventory.json").read_text(encoding="utf-8"))
    profile = json.loads((ROOT / "analysis" / "output" / "style_profile.json").read_text(encoding="utf-8"))
    if len(inventory.get("sources", [])) != 5:
        fail("v0.1 corpus must contain exactly five local source files")
    if profile.get("profiles", {}).get("combined", {}).get("chinese_character_count", 0) < 1_000_000:
        fail("combined profile is unexpectedly small")

    ignored = subprocess.run(
        ["git", "check-ignore", "sources_and_references", "analysis/output/raw"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    if ignored.returncode != 0:
        fail("source books and raw extracts must be ignored by Git")

    tracked = subprocess.run(
        ["git", "ls-files", "sources_and_references", "analysis/output/raw"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    )
    if tracked.stdout.strip():
        fail("a source book or raw extract is tracked")

    print("PASS: skill package, corpus profile, and Git separation are valid")


if __name__ == "__main__":
    main()
