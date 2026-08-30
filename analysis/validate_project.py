#!/usr/bin/env python3
"""Validate the skill package, independent profiles, evals, and Git boundary."""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILL_ROOT = ROOT / "historian-writing"
SKILL = SKILL_ROOT / "SKILL.md"
LOCAL_LINK = re.compile(r"\]\((?!https?://|#)([^)#]+)(?:#[^)]+)?\)")
SAFE_SOURCE_ID = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
ANNA_HASH = "2dbb02eb3d69e09e041a24e8b3edc854dadf1eaa1f326ece91c040c3e5240d9e"
EXPECTED_PROFILES = {"cambridge_china", "toynbee", "anna_translation", "historical_combined"}
FORBIDDEN_PUBLIC_STRINGS = (
    "z" + "-library",
    "1" + "lib.sk",
    "z" + "-lib.sk",
)

REQUIRED = [
    ROOT / "README.md",
    ROOT / "docs" / "corpus-boundaries.md",
    ROOT / "docs" / "methodology.md",
    ROOT / "docs" / "roadmap.md",
    ROOT / "analysis" / "source_catalog.json",
    ROOT / "analysis" / "style-findings.md",
    ROOT / "analysis" / "anna-close-reading-notes.md",
    ROOT / "analysis" / "output" / "corpus_inventory.json",
    ROOT / "analysis" / "output" / "style_profile.json",
    ROOT / "analysis" / "output" / "close_reading_queue.json",
    SKILL_ROOT / "agents" / "openai.yaml",
    SKILL_ROOT / "references" / "ability-library.md",
    SKILL_ROOT / "references" / "evidence-boundaries.md",
    SKILL_ROOT / "references" / "intensity-routing.md",
    SKILL_ROOT / "references" / "literary-language-organization.md",
    SKILL_ROOT / "references" / "quality-gate.md",
    SKILL_ROOT / "references" / "style-signals.md",
    SKILL_ROOT / "references" / "task-modes.md",
    ROOT / "evals" / "README.md",
    ROOT / "evals" / "validate_evals.py",
]


def fail(message: str) -> None:
    raise SystemExit(f"FAIL: {message}")


def public_text_files() -> list[Path]:
    excluded = {".git", "sources_and_references", "raw", "__pycache__"}
    return [
        path for path in ROOT.rglob("*")
        if path.is_file()
        and not excluded.intersection(path.parts)
        and path.suffix.lower() in {".md", ".json", ".py", ".yaml", ".yml"}
    ]


def main() -> None:
    for path in REQUIRED:
        if not path.is_file():
            fail(f"missing required file: {path.relative_to(ROOT)}")
    for index in range(1, 10):
        if not list((ROOT / "evals" / "cases").glob(f"{index:02d}-*.md")):
            fail(f"missing evaluation case {index:02d}")

    skill_text = SKILL.read_text(encoding="utf-8")
    if not skill_text.startswith("---\nname: historian-writing\n"):
        fail("SKILL.md has no valid historian-writing frontmatter")
    if "只在用户明确点名" not in skill_text:
        fail("SKILL.md must retain its explicit-invocation instruction")
    policy = (SKILL_ROOT / "agents" / "openai.yaml").read_text(encoding="utf-8")
    if "allow_implicit_invocation: false" not in policy:
        fail("agents/openai.yaml must reject implicit invocation")

    for document in ROOT.rglob("*.md"):
        if ".git" in document.parts or "sources_and_references" in document.parts or "raw" in document.parts:
            continue
        for target in LOCAL_LINK.findall(document.read_text(encoding="utf-8")):
            destination = (document.parent / target).resolve()
            if not destination.exists():
                fail(f"broken local Markdown link in {document.relative_to(ROOT)}: {target}")
            if document.is_relative_to(SKILL_ROOT) and not destination.is_relative_to(SKILL_ROOT):
                fail(f"skill package has an external local link: {document.relative_to(ROOT)} -> {target}")

    for path in public_text_files():
        text = path.read_text(encoding="utf-8", errors="replace").lower()
        for forbidden in FORBIDDEN_PUBLIC_STRINGS:
            if forbidden in text:
                fail(f"public file exposes a download-site filename fragment: {path.relative_to(ROOT)}")

    catalog = json.loads((ROOT / "analysis" / "source_catalog.json").read_text(encoding="utf-8"))
    inventory = json.loads((ROOT / "analysis" / "output" / "corpus_inventory.json").read_text(encoding="utf-8"))
    profile_doc = json.loads((ROOT / "analysis" / "output" / "style_profile.json").read_text(encoding="utf-8"))
    sources = inventory.get("sources", [])
    if len(catalog.get("sources", [])) != 6 or len(sources) != 6:
        fail("current corpus must contain exactly six catalogued source files")
    if any(not SAFE_SOURCE_ID.fullmatch(str(source.get("source_id", ""))) for source in sources):
        fail("inventory has an unsafe source_id")

    profiles = profile_doc.get("profiles", {})
    if set(profiles) != EXPECTED_PROFILES:
        fail(f"profile keys must be exactly: {', '.join(sorted(EXPECTED_PROFILES))}")
    policy_doc = profile_doc.get("profile_policy", {})
    if policy_doc.get("all_corpus_combined_profile") is not False:
        fail("all-corpus combined profile must remain disabled")
    if policy_doc.get("anna_translation_is_independent") is not True:
        fail("Anna profile must be explicitly independent")
    historical_sum = profiles["cambridge_china"]["chinese_character_count"] + profiles["toynbee"]["chinese_character_count"]
    if profiles["historical_combined"]["chinese_character_count"] != historical_sum:
        fail("historical_combined contains a non-historical collection")

    anna_source = next((source for source in sources if source.get("source_id") == "anna-karenina-zh-gao-fu"), None)
    if anna_source is None or anna_source.get("sha256") != ANNA_HASH:
        fail("Anna source identity does not match the verified EPUB")
    if anna_source.get("archive_member_count") != 311:
        fail("Anna EPUB member count changed")
    if anna_source.get("mimetype_compliant") is not True or anna_source.get("crc_all_passed") is not True:
        fail("Anna EPUB archive validation failed")
    anna = profiles["anna_translation"]
    expected_anna = {
        "unit_count": 250,
        "nonempty_unit_count": 242,
        "chinese_character_count": 525612,
        "paragraph_count": 7310,
        "sentence_count": 21667,
    }
    for field, expected in expected_anna.items():
        if anna.get(field) != expected:
            fail(f"Anna profile {field} changed: expected {expected}, got {anna.get(field)}")
    if anna["sentence_length_chinese_characters"].get("median") != 19:
        fail("Anna sentence median changed")
    if anna["extraction_quality"] != {"replacement_character_count": 0, "html_residue_count": 0}:
        fail("Anna extraction quality check failed")

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

    print("PASS: skill package, independent profiles, eval coverage, and Git separation are valid")


if __name__ == "__main__":
    main()
