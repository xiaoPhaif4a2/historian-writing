#!/usr/bin/env python3
"""Check that the comprehensive writing eval coverage is present."""

from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CASES = ROOT / "evals" / "cases"
REQUIRED_CASE_SIGNALS = {
    "05-flow-and-rhythm.md": ("句子长短", "自然承接", "补写心理", "评述"),
    "06-concrete-to-abstract.md": ("具体到抽象", "实际可达", "人物心理", "社区决定"),
    "07-fidelity-and-evidence.md": ("原意", "证据等级", "前后对照", "补写"),
    "08-negative-official-notice.md": ("公文通知", "克制强度", "可操作性", "修辞"),
    "09-surface-beauty-trap.md": ("表面优美", "形容词", "长句", "隐喻"),
    "10-positive-grounding.md": ("没有违禁词", "谁核定", "下周做什么", "空转"),
    "11-genre-routing-pair.md": ("进展记录", "家长群", "信息顺序", "电梯恢复"),
    "12-calculation-causality-boundary.md": ("计算不等于因果", "随机分流", "点击率", "提交或成交"),
    "13-connector-shell.md": ("连接词外壳", "周三下午", "周六上午", "预先宣布"),
    "14-nonfiction-literary-drift.md": ("小说化诱惑", "1974", "1996", "居民回忆"),
}
RUBRIC_SIGNALS = (
    "对象与动作",
    "文体与去处",
    "关系与段落路径",
    "事实与原意",
    "强度匹配",
    "反向测试方法",
    "硬失败",
)
SMOKE = ROOT / "evals" / "runs" / "2026-08-30-smoke"
SMOKE_SIGNALS = {
    "05-output.md": ("1962", "1978", "1996", "2018", "没有说明他当时怎样想"),
    "06-output.md": ("9:00—17:00", "16:30", "24", "8", "三位"),
    "07-output.md": ("48", "31", "7", "没有调整标识前后的对照数据", "两周"),
    "08-output.md": ("9 月 6 日", "13:30—16:30", "无需疏散", "分机 608"),
    "09-output.md": ("可能", "没有调查", "所有居民"),
}
COMPREHENSIVE_SMOKE = ROOT / "evals" / "runs" / "2026-08-31-comprehensive-smoke"
COMPREHENSIVE_SMOKE_SIGNALS = {
    "10-output.md": ("暂时不马上增加周日开放", "36", "18", "14", "4", "9", "下周"),
    "11-output.md": ("项目组进展记录", "家长群通知", "9 月 6 日 12:00", "6305", "尚未确认"),
    "12-output.md": ("15.5%", "18.6%", "3.1 个百分点", "不能说明", "随机分流"),
    "13-output.md": ("41", "29", "周三下午", "周六上午", "试行四周", "不是预先证明"),
    "14-output.md": ("1974", "1996", "1998", "2015", "不能由说明文字补写"),
}


def fail(message: str) -> None:
    raise SystemExit(f"FAIL: {message}")


def main() -> None:
    for filename, signals in REQUIRED_CASE_SIGNALS.items():
        path = CASES / filename
        if not path.is_file():
            fail(f"missing evaluation case: {filename}")
        text = path.read_text(encoding="utf-8")
        missing = [signal for signal in signals if signal not in text]
        if missing:
            fail(f"{filename} missing signals: {', '.join(missing)}")

    rubric = (ROOT / "evals" / "README.md").read_text(encoding="utf-8")
    missing = [signal for signal in RUBRIC_SIGNALS if signal not in rubric]
    if missing:
        fail(f"evaluation rubric missing: {', '.join(missing)}")

    for filename, signals in SMOKE_SIGNALS.items():
        path = SMOKE / filename
        if not path.is_file():
            fail(f"missing smoke output: {filename}")
        text = path.read_text(encoding="utf-8")
        missing = [signal for signal in signals if signal not in text]
        if missing:
            fail(f"{filename} lost required facts or boundaries: {', '.join(missing)}")
    for filename, limit in {"08-output.md": 140, "09-output.md": 220}.items():
        text = (SMOKE / filename).read_text(encoding="utf-8")
        chinese_count = len(re.findall(r"[\u4e00-\u9fff]", text))
        if chinese_count > limit:
            fail(f"{filename} exceeds {limit} Chinese characters")
    for filename, signals in COMPREHENSIVE_SMOKE_SIGNALS.items():
        path = COMPREHENSIVE_SMOKE / filename
        if not path.is_file():
            fail(f"missing comprehensive smoke output: {filename}")
        text = path.read_text(encoding="utf-8")
        missing = [signal for signal in signals if signal not in text]
        if missing:
            fail(f"{filename} lost comprehensive writing signals: {', '.join(missing)}")
    for filename, limit in {
        "10-output.md": 240,
        "11-output.md": 340,
        "12-output.md": 260,
        "13-output.md": 260,
        "14-output.md": 330,
    }.items():
        text = (COMPREHENSIVE_SMOKE / filename).read_text(encoding="utf-8")
        chinese_count = len(re.findall(r"[\u4e00-\u9fff]", text))
        if chinese_count > limit:
            fail(f"{filename} exceeds {limit} Chinese characters")
    result = ROOT / "evals" / "results" / "2026-08-30-single-run-smoke.md"
    if not result.is_file() or "不构成" not in result.read_text(encoding="utf-8"):
        fail("smoke result must disclose its non-comparative evidence limit")
    comprehensive_result = ROOT / "evals" / "results" / "2026-08-31-comprehensive-single-run-smoke.md"
    if not comprehensive_result.is_file() or "不构成" not in comprehensive_result.read_text(encoding="utf-8"):
        fail("comprehensive smoke result must disclose its non-comparative evidence limit")

    print("PASS: targeted eval coverage and single-run smoke boundaries are valid")


if __name__ == "__main__":
    main()
