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


def choose_quantiles(rows: list[dict[str, object]], count: int) -> list[dict[str, object]]:
    if not rows:
        return []
    indexes = sorted({round((len(rows) - 1) * fraction / max(count - 1, 1)) for fraction in range(count)})
    return [rows[index] for index in indexes]


def main() -> None:
    grouped: dict[str, list[dict[str, object]]] = defaultdict(list)
    for path in sorted(RAW.glob("*.jsonl")):
        for line in path.read_text(encoding="utf-8").splitlines():
            record = json.loads(line)
            if record["chinese_character_count"] >= 600:
                grouped[str(record["source_id"])].append(record)

    queue = []
    for source_id, records in sorted(grouped.items()):
        is_anna = records[0]["collection"] == "anna_translation"
        for record in choose_quantiles(records, count=6 if is_anna else 4):
            queue.append({
                "source_id": source_id,
                "collection": record["collection"],
                "locator": record["locator"],
                "chinese_character_count": record["chinese_character_count"],
                "reading_focus": "literary_language_organization" if is_anna else "historical_explanation",
                "questions": ANNA_QUESTIONS if is_anna else HISTORICAL_QUESTIONS,
            })
    OUT.write_text(json.dumps({"sample_count": len(queue), "samples": queue}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {len(queue)} close-reading locators to {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
