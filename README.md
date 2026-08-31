# 历史学家写作 / historian-writing

一个仅在用户显式调用时使用的中文综合写作 skill。v0.3 在原有历史解释与文学语言组织之上，增加正向表达规范和文体路由：让句子有明确对象和动作，让段落沿真实关系推进，让文本从读者的问题出发并落到含义、后果或行动。它不靠大规模违禁词表定义自然中文，也不把表达做成小说腔。

经过界定的语料仍只提供按功能组织的能力：历史语料负责分析、解释、尺度切换和判断边界；独立的文学中译语料负责句子节奏、自然过渡、具体与抽象转换、叙述距离，以及叙述、人物反应与评述的衔接。运行时不让用户选择作者，也不模仿作者。

## 使用

将完整的 [`historian-writing/`](historian-writing/) 文件夹安装为 Codex skill。它是自包含的，不需要复制原书或分析目录。重新打开 Codex 后，以 `$historian-writing` 调用；只有用户明确点名“历史学家 skill”“历史学家写作”或 `historian-writing` 时才能使用。

适用任务包括问答、说明、通知、邮件、报告、复盘、评论、历史评述、个人叙述与明确的文学创作，也包括从零起草、大幅重写、把零散想法发展成文章和受约束的简单编辑。默认直接交付成稿；需要诊断、教学说明或前后对照时，由用户明确提出。

## 能力、文体与强度

- 正向表达规范要求对象与动作落地、关系产生过渡、段落有来由和去处、具体与概括互相负责。
- 文体路由按通知/办事、报告/复盘、问答/解释、评论/分析、公众说明、个人叙述和文学创作改变信息顺序、详略与落点。
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

项目评测检查对象与动作、文体与落点、段落来由与去处、结构解释、事实与原意边界、语言组织和文学强度。反向案例专门覆盖没有违禁词却仍然空转、同一材料只换标题未换文体、把计算差异升级为因果、连接词替关系工作，以及事实文本受“感染力”要求诱导而小说化。见 [evals/README.md](evals/README.md)。

## 路线

当前仍是可独立安装的指令型 skill。只有持续行为评测显示其存在稳定上限时，才评估模型化方案；不把微调当作预设终点。见 [docs/roadmap.md](docs/roadmap.md)。
