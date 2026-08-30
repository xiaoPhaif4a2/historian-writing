# 历史学家写作 / historian-writing

一个仅在用户显式调用时使用的中文写作 skill。它把经过界定的语料转成按功能组织的能力：历史语料负责文章结构、历史解释、尺度切换和判断边界；独立的文学中译语料负责句子节奏、自然过渡、具体与抽象转换、叙述距离，以及叙述、人物反应与评述的衔接。运行时不让用户选择作者，也不模仿作者。

## 使用

将完整的 [`historian-writing/`](historian-writing/) 文件夹安装为 Codex skill。它是自包含的，不需要复制原书或分析目录。重新打开 Codex 后，以 `$historian-writing` 调用；只有用户明确点名“历史学家 skill”“历史学家写作”或 `historian-writing` 时才能使用。

适用任务包括从零起草、大幅重写、把零散想法发展成文章和受约束的简单编辑。默认直接交付成稿；需要诊断、教学说明或前后对照时，由用户明确提出。

## 能力与强度

- 剑桥中国史与汤因比中译样本支持结构、解释、尺度与判断边界。
- 《安娜·卡列尼娜》高惠群、傅石球中译本作为独立的“文学语言组织”来源，只支持中文表达层面的能力，不迁移小说思想、人物、情节、社会判断或价值立场。
- 文学语言组织自动路由：通知、公文和报告克制；一般写作轻量；评论、随笔和历史评述中度；明确文学创作充分。
- 文学性不等于增加形容词、长句或隐喻。事实文本不能补造场景、心理、对白、引语、事件或数据，不能改变原意与证据等级。

本项目学习的是具体中译本呈现的中文表达，不能称作原作者本人的中文风格。详细边界见 [语料边界](docs/corpus-boundaries.md)、[方法](docs/methodology.md) 和 [语料画像](analysis/style-findings.md)。

## 仓库结构

```text
historian-writing/        可安装的 self-contained skill
analysis/                 本地提取、来源目录与分析脚本
analysis/output/          可提交的聚合统计；全文抽取被忽略
evals/                    正向、反向与边界评测
docs/                     方法、语料边界与路线图
sources_and_references/   本地原书，始终被 Git 忽略
```

`analysis/source_catalog.json` 以 SHA-256 匹配本地文件，并只向公开结果写入安全 `source_id`。运行分析：

```powershell
& <python-with-pypdf> .\analysis\analyze_corpus.py
& <python> .\analysis\select_close_reading.py
```

脚本仅把全文写入 `analysis/output/raw/`。公开画像保留 `cambridge_china`、`toynbee`、`historical_combined` 与独立 `anna_translation`；不存在把 Anna 并入的总体 `combined`。

## 验收

```powershell
& <python> .\evals\validate_evals.py
& <python> .\analysis\validate_project.py
& <python> <skill-creator>\scripts\quick_validate.py .\historian-writing
```

项目评测检查结构解释、前后流畅节奏、具体到抽象的过渡、事实与原意边界、通知公文的反向路由，以及是否只做了形容词、长句或隐喻层面的表面美化。见 [evals/README.md](evals/README.md)。

## 路线

当前仍是可独立安装的指令型 skill。只有持续行为评测显示其存在稳定上限时，才评估模型化方案；不把微调当作预设终点。见 [docs/roadmap.md](docs/roadmap.md)。
