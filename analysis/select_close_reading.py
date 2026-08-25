#!/usr/bin/env python3
"""Create a stratified, non-quoting queue for human close reading.

The queue stores source names and locators only.  Read the corresponding local
JSONL record under analysis/output/raw/ when performing close reading; never
copy the book text into the public report.
"""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "analysis" / "output" / "raw"
OUT = ROOT / "analysis" / "output" / "close_reading_queue.json"


def choose_quantiles(rows: list[dict[str, object]], count: int = 4) -> list[dict[str, object]]:
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
                grouped[record["source"]].append(record)

    queue = []
    for source, records in sorted(grouped.items()):
        for record in choose_quantiles(records):
            queue.append({
                "source": source,
                "collection": record["collection"],
                "locator": record["locator"],
                "chinese_character_count": record["chinese_character_count"],
                "questions": [
                    "本段承担什么结构任务？",
                    "判断如何连接条件、机制、材料、反向力量或结果？",
                    "句子节奏和连接方式怎样服务该任务？",
                    "哪些部分只属于该材料或译者，不能升级成通用规则？",
                ],
            })
    OUT.write_text(json.dumps({"sample_count": len(queue), "samples": queue}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {len(queue)} close-reading locators to {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
