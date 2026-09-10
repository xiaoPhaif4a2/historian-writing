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
BALZAC_HASH = "179d06ca93037ab3226a6fdf0c8003c574d1fd6b3533507bb62c099b24e0d952"
EXPECTED_PROFILES = {
    "cambridge_china",
    "toynbee",
    "anna_translation",
    "balzac_translation",
    "historical_combined",
}
INDEPENDENT_LITERARY_PROFILES = ["anna_translation", "balzac_translation"]
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
    ROOT / "analysis" / "balzac-close-reading-notes.md",
    ROOT / "analysis" / "output" / "corpus_inventory.json",
    ROOT / "analysis" / "output" / "style_profile.json",
    ROOT / "analysis" / "output" / "close_reading_queue.json",
    SKILL_ROOT / "agents" / "openai.yaml",
    SKILL_ROOT / "references" / "ability-library.md",
    SKILL_ROOT / "references" / "evidence-boundaries.md",
    SKILL_ROOT / "references" / "expression-principles.md",
    SKILL_ROOT / "references" / "genre-routing.md",
    SKILL_ROOT / "references" / "intensity-routing.md",
    SKILL_ROOT / "references" / "literary-language-organization.md",
    SKILL_ROOT / "references" / "quality-gate.md",
    SKILL_ROOT / "references" / "social-texture.md",
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
    for index in range(1, 18):
        if not list((ROOT / "evals" / "cases").glob(f"{index:02d}-*.md")):
            fail(f"missing evaluation case {index:02d}")

    skill_text = SKILL.read_text(encoding="utf-8")
    if not skill_text.startswith("---\nname: historian-writing\n"):
        fail("SKILL.md has no valid historian-writing frontmatter")
    if "只在用户明确点名" not in skill_text:
        fail("SKILL.md must retain its explicit-invocation instruction")
    for signal in (
        "问题发动机",
        "历史发动机",
        "人性发动机",
        "语言发动机",
        "social-texture.md",
        "陌生化、反事实、代价、双尺度与余波",
    ):
        if signal not in skill_text:
            fail(f"SKILL.md missing comprehensive writing signal: {signal}")
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
    if len(catalog.get("sources", [])) != 7 or len(sources) != 7:
        fail("current corpus must contain exactly seven catalogued source files")
    if any(not SAFE_SOURCE_ID.fullmatch(str(source.get("source_id", ""))) for source in sources):
        fail("inventory has an unsafe source_id")

    profiles = profile_doc.get("profiles", {})
    if set(profiles) != EXPECTED_PROFILES:
        fail(f"profile keys must be exactly: {', '.join(sorted(EXPECTED_PROFILES))}")
    policy_doc = profile_doc.get("profile_policy", {})
    if policy_doc.get("all_corpus_combined_profile") is not False:
        fail("all-corpus combined profile must remain disabled")
    if policy_doc.get("independent_literary_profiles") != INDEPENDENT_LITERARY_PROFILES:
        fail("Anna and Balzac profiles must be explicitly independent")
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

    balzac_source = next((source for source in sources if source.get("source_id") == "pere-goriot-zh-fu-lei"), None)
    if balzac_source is None or balzac_source.get("sha256") != BALZAC_HASH:
        fail("Balzac source identity does not match the verified EPUB")
    if balzac_source.get("archive_member_count") != 33:
        fail("Balzac EPUB member count changed")
    if balzac_source.get("mimetype_compliant") is not True or balzac_source.get("crc_all_passed") is not True:
        fail("Balzac EPUB archive validation failed")
    if balzac_source.get("extraction_scope") != "body from Text/chapter1.xhtml through Text/chapter6.xhtml":
        fail("Balzac body boundary changed")
    balzac = profiles["balzac_translation"]
    expected_balzac = {
        "unit_count": 6,
        "nonempty_unit_count": 6,
        "chinese_character_count": 132631,
        "paragraph_count": 1752,
        "sentence_count": 6218,
    }
    for field, expected in expected_balzac.items():
        if balzac.get(field) != expected:
            fail(f"Balzac profile {field} changed: expected {expected}, got {balzac.get(field)}")
    if balzac["sentence_length_chinese_characters"].get("median") != 18:
        fail("Balzac sentence median changed")
    if balzac["extraction_quality"] != {"replacement_character_count": 0, "html_residue_count": 0}:
        fail("Balzac extraction quality check failed")

    queue = json.loads((ROOT / "analysis" / "output" / "close_reading_queue.json").read_text(encoding="utf-8"))
    balzac_samples = [
        sample for sample in queue.get("samples", [])
        if sample.get("collection") == "balzac_translation"
    ]
    functions = {
        "object_as_evidence",
        "space_as_hierarchy",
        "social_circulation",
        "desire_institutionalized",
        "local_to_social_order",
    }
    if len(balzac_samples) != 15:
        fail("Balzac close-reading queue must contain exactly 15 samples")
    for function in functions:
        if sum(sample.get("candidate_function") == function for sample in balzac_samples) != 3:
            fail(f"Balzac close-reading queue must contain three samples for {function}")

    ignored = subprocess.run(
        [
            "git",
            "check-ignore",
            "--no-index",
            "sources_and_references/validation-placeholder",
            "analysis/output/raw/validation-placeholder",
        ],
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
