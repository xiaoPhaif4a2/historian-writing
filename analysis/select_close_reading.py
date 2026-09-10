#!/usr/bin/env python3
"""Create a stratified, non-quoting queue for local close reading."""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "analysis" / "output" / "raw"
OUT = ROOT / "analysis" / "output" / "close_reading_queue.json"

HISTORICAL_QUESTIONS = [
    "本段承担什么结构或历史解释任务？",
    "判断如何连接条件、机制、材料、反向力量或结果？",
    "尺度、句子节奏和连接方式怎样服务该任务？",
    "哪些部分只属于该材料或译者，不能升级成通用规则？",
]

ANNA_QUESTIONS = [
    "叙述、人物反应与评论怎样自然衔接？",
    "具体细节怎样承载含义，并在何处转入抽象判断？",
    "叙述距离、句子长短和段落过渡怎样共同调节节奏？",
    "哪些内容属于人物、情节、价值立场或译者选择，必须留在原作中？",
]

SOCIAL_TEXTURE_FUNCTIONS = {
    "object_as_evidence": {
        "markers": ("衣服", "家具", "银器", "首饰", "马车", "请帖", "房租", "饭桌", "屋子"),
        "question": "物件怎样证明人物之间的资源、债务、身份或依附关系，而不只是布景？",
    },
    "space_as_hierarchy": {
        "markers": ("公寓", "客厅", "饭厅", "房间", "楼上", "楼下", "街", "舞会", "府上"),
        "question": "空间的进入、隔离、远近或上下关系怎样改变人物可采取的行动？",
    },
    "social_circulation": {
        "markers": ("钱", "法郎", "债", "财产", "收入", "职位", "名誉", "婚姻", "嫁妆"),
        "question": "金钱、职位、名誉或亲情怎样经由可追踪的交换链改变行动条件？",
    },
    "desire_institutionalized": {
        "markers": ("资格", "门第", "介绍", "请柬", "婚事", "银行", "法律", "社会", "出身"),
        "question": "欲望怎样取得制度形式：需要哪种资格、关系、程序、职位或认可？",
    },
    "local_to_social_order": {
        "markers": ("巴黎", "社会", "上流", "穷人", "富人", "贵族", "商人", "学生", "公寓"),
        "question": "局部场所怎样通过人物流动、资源交换或评价规则连接更大的社会秩序？",
    },
}

SOCIAL_TEXTURE_COMMON_QUESTIONS = [
    "删除形容词和评价词后，社会关系与作用机制是否仍能成立？",
    "哪些人物、情节、固定句式、价值判断或时代类型化偏见必须留在原作？",
]


def choose_quantiles(rows: list[dict[str, object]], count: int) -> list[dict[str, object]]:
    if not rows:
        return []
    indexes = sorted({round((len(rows) - 1) * fraction / max(count - 1, 1)) for fraction in range(count)})
    return [rows[index] for index in indexes]


def balzac_candidates(records: list[dict[str, object]]) -> list[dict[str, object]]:
    candidates = []
    for record in records:
        for paragraph_index, paragraph in enumerate(str(record["text"]).splitlines(), start=1):
            chinese_count = sum("\u4e00" <= char <= "\u9fff" for char in paragraph)
            if chinese_count < 60:
                continue
            for function, spec in SOCIAL_TEXTURE_FUNCTIONS.items():
                hits = sum(paragraph.count(marker) for marker in spec["markers"])
                if hits:
                    candidates.append({
                        "source_id": record["source_id"],
                        "collection": record["collection"],
                        "locator": f'{record["locator"]};paragraph:{paragraph_index}',
                        "chinese_character_count": chinese_count,
                        "reading_focus": "social_texture",
                        "candidate_function": function,
                        "selection_marker_hits": hits,
                        "questions": [spec["question"], *SOCIAL_TEXTURE_COMMON_QUESTIONS],
                    })
    selected = []
    used_locators: set[str] = set()
    for function in SOCIAL_TEXTURE_FUNCTIONS:
        ranked = sorted(
            (item for item in candidates if item["candidate_function"] == function),
            key=lambda item: (-int(item["selection_marker_hits"]), str(item["locator"])),
        )
        distinct_units = []
        fallback = []
        used_units: set[str] = set()
        for item in ranked:
            if item["locator"] in used_locators:
                continue
            unit = str(item["locator"]).split(";paragraph:", 1)[0]
            if unit not in used_units:
                distinct_units.append(item)
                used_units.add(unit)
            else:
                fallback.append(item)
        for item in (distinct_units + fallback)[:3]:
            selected.append(item)
            used_locators.add(str(item["locator"]))
    return selected


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--incremental", action="store_true", help="retain queued samples for sources without local raw text")
    args = parser.parse_args()

    grouped: dict[str, list[dict[str, object]]] = defaultdict(list)
    for path in sorted(RAW.glob("*.jsonl")):
        for line in path.read_text(encoding="utf-8").splitlines():
            record = json.loads(line)
            if record["chinese_character_count"] >= 600:
                grouped[str(record["source_id"])].append(record)

    queue = []
    for source_id, records in sorted(grouped.items()):
        collection = records[0]["collection"]
        if collection == "balzac_translation":
            queue.extend(balzac_candidates(records))
            continue
        is_anna = collection == "anna_translation"
        for record in choose_quantiles(records, count=6 if is_anna else 4):
            queue.append({
                "source_id": source_id,
                "collection": record["collection"],
                "locator": record["locator"],
                "chinese_character_count": record["chinese_character_count"],
                "reading_focus": "literary_language_organization" if is_anna else "historical_explanation",
                "questions": ANNA_QUESTIONS if is_anna else HISTORICAL_QUESTIONS,
            })
    if args.incremental and OUT.is_file():
        current_ids = set(grouped)
        prior = json.loads(OUT.read_text(encoding="utf-8")).get("samples", [])
        queue = [sample for sample in prior if str(sample.get("source_id")) not in current_ids] + queue
    OUT.write_text(json.dumps({"sample_count": len(queue), "samples": queue}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {len(queue)} close-reading locators to {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
