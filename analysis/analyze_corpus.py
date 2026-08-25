#!/usr/bin/env python3
"""Extract local PDF/EPUB sources and produce a non-quoting style profile.

Raw extracted text stays under analysis/output/raw/ (gitignored).  The tracked
outputs contain only metadata, quality indicators, locators, and aggregate
statistics so that the public repository does not redistribute source books.
"""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
import statistics
import zipfile
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from html.parser import HTMLParser
from pathlib import Path
from typing import Iterable
from xml.etree import ElementTree as ET


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCES = ROOT / "sources_and_references"
DEFAULT_OUTPUT = ROOT / "analysis" / "output"

SENTENCE_ENDINGS = re.compile(r"(?<=[。！？；])")
CHINESE_CHAR = re.compile(r"[\u4e00-\u9fff]")
SPACE = re.compile(r"[ \t\u3000]+")
MULTI_BLANK = re.compile(r"\n{3,}")
PAGE_NUMBER = re.compile(r"^\s*[—\-–]?\s*\d{1,4}\s*[—\-–]?\s*$")

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
    source: str
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


def classify_collection(name: str) -> str:
    if "剑桥" in name:
        return "cambridge_china"
    if "汤因比" in name:
        return "toynbee"
    return "unclassified"


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


def extract_pdf(path: Path) -> list[Unit]:
    try:
        from pypdf import PdfReader
    except ImportError as exc:
        raise RuntimeError("pypdf is required to extract PDF sources.") from exc

    reader = PdfReader(str(path))
    if reader.is_encrypted:
        reader.decrypt("")
    collection = classify_collection(path.name)
    units = []
    for page_number, page in enumerate(reader.pages, start=1):
        units.append(Unit(collection, path.name, f"page:{page_number}", normalize_text(page.extract_text() or "")))
    return units


def opf_path(archive: zipfile.ZipFile) -> str:
    container = ET.fromstring(archive.read("META-INF/container.xml"))
    rootfile = container.find(".//{*}rootfile")
    if rootfile is None or not rootfile.attrib.get("full-path"):
        raise RuntimeError("EPUB container has no package document.")
    return rootfile.attrib["full-path"]


def extract_epub(path: Path) -> list[Unit]:
    collection = classify_collection(path.name)
    units = []
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
            member = (package_dir / href).as_posix()
            try:
                raw = archive.read(member).decode("utf-8", errors="replace")
            except KeyError:
                continue
            parser = TextExtractor()
            parser.feed(raw)
            units.append(Unit(collection, path.name, f"spine:{index};file:{href}", parser.result()))
    return units


def sentence_lengths(text: str) -> list[int]:
    return [len(CHINESE_CHAR.findall(sentence)) for sentence in SENTENCE_ENDINGS.split(text) if len(CHINESE_CHAR.findall(sentence)) >= 4]


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
    combined = "\n".join(texts)
    sentences = [length for text in texts for length in sentence_lengths(text)]
    marker_counts = {
        group: {marker: combined.count(marker) for marker in markers}
        for group, markers in MARKER_GROUPS.items()
    }
    chinese_characters = len(CHINESE_CHAR.findall(combined))
    return {
        "unit_count": len(all_units),
        "nonempty_unit_count": len(texts),
        "chinese_character_count": chinese_characters,
        "mean_unit_chinese_characters": round(chinese_characters / len(texts), 2) if texts else 0,
        "sentence_count": len(sentences),
        "sentence_length_chinese_characters": {
            "mean": round(statistics.mean(sentences), 2) if sentences else None,
            "median": round(statistics.median(sentences), 2) if sentences else None,
            "p25": percentile(sentences, 0.25),
            "p75": percentile(sentences, 0.75),
        },
        "markers_per_1000_chinese_characters": {
            group: {marker: round(count * 1000 / chinese_characters, 3) if chinese_characters else 0 for marker, count in counts.items()}
            for group, counts in marker_counts.items()
        },
    }


def raw_record(unit: Unit) -> dict[str, object]:
    chinese = len(CHINESE_CHAR.findall(unit.text))
    return {
        "collection": unit.collection,
        "source": unit.source,
        "locator": unit.locator,
        "chinese_character_count": chinese,
        "text": unit.text,
    }


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def run(sources: Path, output: Path) -> None:
    raw_dir = output / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    output.mkdir(parents=True, exist_ok=True)

    units_by_collection: dict[str, list[Unit]] = defaultdict(list)
    inventory = []
    for path in sorted(sources.iterdir()):
        if not path.is_file() or path.suffix.lower() not in {".pdf", ".epub"}:
            continue
        print(f"Extracting {path.name}", flush=True)
        if path.suffix.lower() == ".pdf":
            units = extract_pdf(path)
        else:
            units = extract_epub(path)
        collection = classify_collection(path.name)
        units_by_collection[collection].extend(units)
        raw_path = raw_dir / f"{path.stem}.jsonl"
        with raw_path.open("w", encoding="utf-8") as handle:
            for unit in units:
                handle.write(json.dumps(raw_record(unit), ensure_ascii=False) + "\n")
        inventory.append({
            "source": path.name,
            "collection": collection,
            "format": path.suffix.lower().lstrip("."),
            "bytes": path.stat().st_size,
            "sha256": sha256(path),
            "extracted_unit_count": len(units),
            "nonempty_unit_count": sum(bool(unit.text) for unit in units),
            "extracted_chinese_character_count": sum(len(CHINESE_CHAR.findall(unit.text)) for unit in units),
        })

    profiles = {collection: profile(units) for collection, units in sorted(units_by_collection.items())}
    profiles["combined"] = profile(unit for units in units_by_collection.values() for unit in units)
    write_json(output / "corpus_inventory.json", {"sources": inventory})
    write_json(output / "style_profile.json", {"marker_groups": MARKER_GROUPS, "profiles": profiles})
    print("Wrote corpus_inventory.json and style_profile.json", flush=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sources", type=Path, default=DEFAULT_SOURCES)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    if not args.sources.is_dir():
        raise SystemExit(f"Source directory does not exist: {args.sources}")
    run(args.sources, args.output)


if __name__ == "__main__":
    main()
