# 历史学家写作 / historian-writing

一个仅在用户显式调用时使用的中文写作 skill。它从经过界定的历史著作中提炼可复用的写作能力，用于起草、重写和把零散想法落成文章；它不让用户选择或显示具体模仿对象。

第一版把《剑桥中国晚清史》《剑桥中华民国史》四卷作为一个集体样本，并结合现有汤因比中译著作。目标是更有解释力、结构层次和叙述控制的中文写作，而不是复刻某位作者的口癖。

## 使用

将完整的 [`historian-writing/`](historian-writing/) 文件夹安装为 Codex skill。它是自包含的：只需该文件夹内的 `SKILL.md` 与 `references/`，不需要复制原书或分析目录。

在 Windows PowerShell 中，从已克隆的仓库根目录运行：

```powershell
Copy-Item -Recurse -Force .\historian-writing "$env:USERPROFILE\.codex\skills\historian-writing"
```

重新打开 Codex 后，以 `$historian-writing` 调用。仅当用户明确点名“历史学家 skill”“历史学家写作”或 `historian-writing` 时调用。

它适合三类任务：

- 从零起草文章；
- 大幅重写既有草稿；
- 将零散观点、材料或提纲发展成文章。

默认直接交付所需成稿。需要诊断、教学说明或前后对照时，用户应明确提出。

## 方法边界

- 该 skill 学习的是现有中文译本呈现的写作方法，不声称还原原作者的英文语言。
- 事实性文本保留用户给出的事实和观点；可以展开背景联系、比较和假设，不能把联想出的事件、数据、引语或人物观点写成事实。
- 它默认不把写作任务扩大为事实研究。用户明确授权研究时，才另行核验资料。
- 输出不标注“仿费正清”“仿汤因比”等来源；README 与文档公开说明方法与语料边界。

详细边界见 [docs/corpus-boundaries.md](docs/corpus-boundaries.md)、[docs/methodology.md](docs/methodology.md) 和 [analysis/style-findings.md](analysis/style-findings.md)。

## 仓库结构

```text
historian-writing/        可安装的 skill
analysis/                 本地提取与分析脚本
analysis/output/          可提交的统计结果；原始提取文本被忽略
evals/                    正向、反向与对照评测
docs/                     方法、语料边界与路线图
sources_and_references/   本地原书，始终被 Git 忽略
```

运行本地分析：

```powershell
& <python> .\analysis\analyze_corpus.py
```

脚本只将原始抽取文本写入被忽略的 `analysis/output/raw/`；版本库中的结果是元数据和聚合统计。

## 验收

评测同时检查：

1. 判断是否呈现条件、机制、制约与结果；
2. 段落是否承担明确功能并有推进关系；
3. 时间、空间和观察尺度切换是否清晰；
4. 句式、连接和判断语气是否符合经语料验证的规律；
5. 是否避免空洞宏大词、机械长句和无证据断言；
6. 是否保留用户原意与确定事实；
7. 在盲评中是否比普通版本更像成熟的历史写作。

评测案例和评分表见 [evals/README.md](evals/README.md)。

## 远期路线

本项目当前是可独立使用的 skill。未来只有当评测表明指令与能力库存在稳定上限时，才评估微调或其他模型化方案；不把训练模型当作预设终点。见 [docs/roadmap.md](docs/roadmap.md)。
