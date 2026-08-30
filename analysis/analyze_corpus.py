#!/usr/bin/env python3
"""Extract catalogued local sources and write non-quoting corpus profiles.

Raw extracted text stays under analysis/output/raw/ (gitignored). Public
outputs use stable source IDs from analysis/source_catalog.json and contain
only metadata, quality indicators, locators, and aggregate statistics.
"""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
import statistics
import zipfile
from collections import defaultdict
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path
from typing import Iterable
from xml.etree import ElementTree as ET


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCES = ROOT / "sources_and_references"
DEFAULT_OUTPUT = ROOT / "analysis" / "output"
DEFAULT_CATALOG = ROOT / "analysis" / "source_catalog.json"
HISTORICAL_COLLECTIONS = frozenset({"cambridge_china", "toynbee"})

SENTENCE_ENDINGS = re.compile(r"(?<=[。！？；])")
CHINESE_CHAR = re.compile(r"[\u4e00-\u9fff]")
SPACE = re.compile(r"[ \t\u3000]+")
MULTI_BLANK = re.compile(r"\n{3,}")
PAGE_NUMBER = re.compile(r"^\s*[—\-–]?\s*\d{1,4}\s*[—\-–]?\s*$")
HTML_RESIDUE = re.compile(r"<[A-Za-z][^>\n]{0,200}>")

MARKER_GROUPS = {
    "因果": ("因此", "因而", "从而", "由于", "导致", "结果", "使得", "原因", "后果"),
    "转折限定": ("然而", "但是", "不过", "尽管", "虽然", "却", "反而", "同时", "另一方面"),
    "例证具体化": ("例如", "比如", "譬如", "尤其", "具体说来", "实际上"),
    "判断留白": ("可能", "似乎", "可以说", "未必", "大概", "往往", "倾向于", "不能简单地"),
    "时间尺度": ("世纪", "年代", "时期", "阶段", "长期", "短期", "此后", "此前", "与此同时"),
    "比较关系": ("相比", "相较", "不同于", "而不是", "一方面", "另一方面", "既", "又"),
}


@dataclass
class Unit:
    collection: str
    source_id: str
    locator: str
    text: str


class TextExtractor(HTMLParser):
    """Turn XHTML into readable text without retaining markup or media."""

    BLOCK_TAGS = {"p", "div", "section", "article", "li", "h1", "h2", "h3", "h4", "blockquote", "br", "tr"}
    IGNORE_TAGS = {"script", "style", "svg", "nav", "head"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.ignore_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in self.IGNORE_TAGS:
            self.ignore_depth += 1
        elif tag in self.BLOCK_TAGS and not self.ignore_depth:
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in self.IGNORE_TAGS and self.ignore_depth:
            self.ignore_depth -= 1
        elif tag in self.BLOCK_TAGS and not self.ignore_depth:
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        if not self.ignore_depth:
            self.parts.append(data)

    def result(self) -> str:
        return normalize_text("".join(self.parts))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_catalog(path: Path) -> dict[str, dict[str, object]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    sources = data.get("sources", [])
    by_hash: dict[str, dict[str, object]] = {}
    for source in sources:
        digest = str(source["sha256"]).lower()
        if digest in by_hash:
            raise RuntimeError(f"Duplicate SHA-256 in source catalog: {digest}")
        by_hash[digest] = source
    return by_hash


def normalize_text(value: str) -> str:
    value = html.unescape(value).replace("\r\n", "\n").replace("\r", "\n")
    kept_lines = []
    for line in value.split("\n"):
        line = SPACE.sub(" ", line).strip()
        if PAGE_NUMBER.match(line):
            continue
        kept_lines.append(line)
    value = "\n".join(kept_lines)
    return MULTI_BLANK.sub("\n\n", value).strip()


def extract_pdf(path: Path, source: dict[str, object]) -> list[Unit]:
    try:
        from pypdf import PdfReader
    except ImportError as exc:
        raise RuntimeError("pypdf is required to extract PDF sources.") from exc

    reader = PdfReader(str(path))
    if reader.is_encrypted:
        reader.decrypt("")
    units = []
    for page_number, page in enumerate(reader.pages, start=1):
        units.append(Unit(
            str(source["collection"]),
            str(source["source_id"]),
            f"page:{page_number}",
            normalize_text(page.extract_text() or ""),
        ))
    return units


def opf_path(archive: zipfile.ZipFile) -> str:
    container = ET.fromstring(archive.read("META-INF/container.xml"))
    rootfile = container.find(".//{*}rootfile")
    if rootfile is None or not rootfile.attrib.get("full-path"):
        raise RuntimeError("EPUB container has no package document.")
    return rootfile.attrib["full-path"]


def epub_quality(path: Path) -> dict[str, object]:
    with zipfile.ZipFile(path) as archive:
        names = archive.namelist()
        mimetype_ok = bool(names) and names[0] == "mimetype" and archive.read("mimetype") == b"application/epub+zip"
        return {
            "archive_member_count": len(names),
            "mimetype_compliant": mimetype_ok,
            "crc_all_passed": archive.testzip() is None,
        }


def extract_epub(path: Path, source: dict[str, object]) -> list[Unit]:
    units = []
    start_href = source.get("epub_body_start_href")
    started = start_href is None
    with zipfile.ZipFile(path) as archive:
        package_path = opf_path(archive)
        package_dir = Path(package_path).parent
        package = ET.fromstring(archive.read(package_path))
        manifest = {
            item.attrib["id"]: item.attrib.get("href", "")
            for item in package.findall(".//{*}manifest/{*}item")
            if item.attrib.get("media-type") in {"application/xhtml+xml", "text/html"}
        }
        spine_ids = [item.attrib["idref"] for item in package.findall(".//{*}spine/{*}itemref")]
        for index, item_id in enumerate(spine_ids, start=1):
            href = manifest.get(item_id)
            if not href:
                continue
            if not started and href == start_href:
                started = True
            if not started:
                continue
            member = (package_dir / href).as_posix()
            try:
                raw = archive.read(member).decode("utf-8", errors="replace")
            except KeyError:
                continue
            parser = TextExtractor()
            parser.feed(raw)
            units.append(Unit(
                str(source["collection"]),
                str(source["source_id"]),
                f"spine:{index};file:{href}",
                parser.result(),
            ))
    if start_href is not None and not started:
        raise RuntimeError(f"Configured EPUB body start not found for {source['source_id']}: {start_href}")
    return units


def sentence_lengths(text: str) -> list[int]:
    return [
        len(CHINESE_CHAR.findall(sentence))
        for sentence in SENTENCE_ENDINGS.split(text)
        if len(CHINESE_CHAR.findall(sentence)) >= 4
    ]


def percentile(values: list[int], fraction: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    index = (len(ordered) - 1) * fraction
    lower, upper = int(index), min(int(index) + 1, len(ordered) - 1)
    return round(ordered[lower] + (ordered[upper] - ordered[lower]) * (index - lower), 2)


def profile(units: Iterable[Unit]) -> dict[str, object]:
    all_units = list(units)
    texts = [unit.text for unit in all_units if unit.text]
    joined = "\n".join(texts)
    sentences = [length for text in texts for length in sentence_lengths(text)]
    paragraphs = [
        line
        for text in texts
        for line in text.splitlines()
        if len(CHINESE_CHAR.findall(line)) >= 8
    ]
    marker_counts = {
        group: {marker: joined.count(marker) for marker in markers}
        for group, markers in MARKER_GROUPS.items()
    }
    chinese_characters = len(CHINESE_CHAR.findall(joined))
    return {
        "unit_count": len(all_units),
        "nonempty_unit_count": len(texts),
        "chinese_character_count": chinese_characters,
        "paragraph_count": len(paragraphs),
        "paragraph_definition": "nonempty line with at least 8 Chinese characters",
        "mean_unit_chinese_characters": round(chinese_characters / len(texts), 2) if texts else 0,
        "sentence_count": len(sentences),
        "sentence_length_chinese_characters": {
            "mean": round(statistics.mean(sentences), 2) if sentences else None,
            "median": round(statistics.median(sentences), 2) if sentences else None,
            "p25": percentile(sentences, 0.25),
            "p75": percentile(sentences, 0.75),
            "maximum": max(sentences) if sentences else None,
        },
        "extraction_quality": {
            "replacement_character_count": joined.count("\ufffd"),
            "html_residue_count": len(HTML_RESIDUE.findall(joined)),
        },
        "markers_per_1000_chinese_characters": {
            group: {
                marker: round(count * 1000 / chinese_characters, 3) if chinese_characters else 0
                for marker, count in counts.items()
            }
            for group, counts in marker_counts.items()
        },
    }


def raw_record(unit: Unit) -> dict[str, object]:
    return {
        "collection": unit.collection,
        "source_id": unit.source_id,
        "locator": unit.locator,
        "chinese_character_count": len(CHINESE_CHAR.findall(unit.text)),
        "text": unit.text,
    }


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def run(sources: Path, output: Path, catalog_path: Path) -> None:
    raw_dir = output / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    output.mkdir(parents=True, exist_ok=True)
    catalog = load_catalog(catalog_path)

    units_by_collection: dict[str, list[Unit]] = defaultdict(list)
    inventory = []
    seen_ids: set[str] = set()
    seen_hashes: set[str] = set()
    for path in sorted(sources.iterdir()):
        if not path.is_file() or path.suffix.lower() not in {".pdf", ".epub"}:
            continue
        digest = sha256(path)
        source = catalog.get(digest)
        if source is None:
            raise RuntimeError(f"Uncatalogued source SHA-256: {digest}")
        source_id = str(source["source_id"])
        if source_id in seen_ids:
            raise RuntimeError(f"Duplicate source content for source_id: {source_id}")
        seen_ids.add(source_id)
        seen_hashes.add(digest)
        print(f"Extracting {source_id}", flush=True)
        if path.suffix.lower() == ".pdf":
            units = extract_pdf(path, source)
            archive_quality: dict[str, object] = {}
        else:
            units = extract_epub(path, source)
            archive_quality = epub_quality(path)
        collection = str(source["collection"])
        units_by_collection[collection].extend(units)
        raw_path = raw_dir / f"{source_id}.jsonl"
        with raw_path.open("w", encoding="utf-8") as handle:
            for unit in units:
                handle.write(json.dumps(raw_record(unit), ensure_ascii=False) + "\n")
        public_source = {key: value for key, value in source.items() if key != "epub_body_start_href"}
        public_source.update({
            "format": path.suffix.lower().lstrip("."),
            "bytes": path.stat().st_size,
            "extracted_unit_count": len(units),
            "nonempty_unit_count": sum(bool(unit.text) for unit in units),
            "extracted_chinese_character_count": sum(len(CHINESE_CHAR.findall(unit.text)) for unit in units),
            **archive_quality,
        })
        if source.get("epub_body_start_href"):
            public_source["extraction_scope"] = f"body from {source['epub_body_start_href']}"
        inventory.append(public_source)

    missing = sorted(set(catalog) - seen_hashes)
    if missing:
        raise RuntimeError(f"Catalogued sources missing from source directory: {', '.join(missing)}")

    profiles = {collection: profile(units) for collection, units in sorted(units_by_collection.items())}
    historical_units = (
        unit
        for collection, units in units_by_collection.items()
        if collection in HISTORICAL_COLLECTIONS
        for unit in units
    )
    profiles["historical_combined"] = profile(historical_units)
    write_json(output / "corpus_inventory.json", {"sources": sorted(inventory, key=lambda item: item["source_id"])})
    write_json(output / "style_profile.json", {
        "profile_policy": {
            "historical_combined_includes": sorted(HISTORICAL_COLLECTIONS),
            "anna_translation_is_independent": True,
            "all_corpus_combined_profile": False,
        },
        "marker_groups": MARKER_GROUPS,
        "profiles": profiles,
    })
    print("Wrote corpus_inventory.json and style_profile.json", flush=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sources", type=Path, default=DEFAULT_SOURCES)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--catalog", type=Path, default=DEFAULT_CATALOG)
    args = parser.parse_args()
    if not args.sources.is_dir():
        raise SystemExit(f"Source directory does not exist: {args.sources}")
    if not args.catalog.is_file():
        raise SystemExit(f"Source catalog does not exist: {args.catalog}")
    run(args.sources, args.output, args.catalog)


if __name__ == "__main__":
    main()
