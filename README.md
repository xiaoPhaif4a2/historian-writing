# 历史学家写作 / historian-writing

一个仅在用户显式调用时使用的“历史—文学思想写作器”。它把用户已有的材料、判断与感受发展成具有问题意识、历史纵深、人性重量和文学形式的中文思想文本，同时把立场、事实权限与创作权留在用户手中。它不是通用润色器，也不提供作者模仿模式。

## 使用

将完整的 [`historian-writing/`](historian-writing/) 文件夹安装为 Codex skill。重新打开 Codex 后，以 `$historian-writing` 调用；只有用户明确点名“历史学家 skill”“历史学家写作”或 `historian-writing` 时才使用。

适用任务包括历史解释与评述、社会文化评论、观念或人物论述、思想随笔、个人叙述、文学性非虚构，以及明确授权的文学创作；可从零起草、重写或发展零散材料。普通通知、邮件、公文和与思想写作无关的通用润色不属于默认范围。

## 四个发动机

- 问题发动机：从主题中找出反常、冲突、隐含前提、代价或未结束的后果。
- 历史发动机：组织条件、变化、机制、尺度、限度与余波。
- 人性发动机：同时保留欲望、约束、选择、责任和代价，拒绝阶级脸谱。
- 语言发动机：让具体材料、段落路径、叙述距离与节奏服从思想。

深度通过陌生化、反事实、代价、双尺度和余波五项测试；忠实、证据 / 创作权限与反伪深刻是不能用语言效果抵销的硬门。

## 语料职责

- 剑桥中国史与汤因比中译样本支持历史解释、尺度切换和判断边界。
- 《安娜·卡列尼娜》高惠群、傅石球中译本作为独立 `anna_translation`，只支持文学语言组织。
- 《高老头》傅雷中译本作为独立 `balzac_translation`，只支持社会肌理：物件作证、空间设限、社会流通、欲望的制度形式与局部—秩序连接。

三个职责不计算跨语料平均。运行时按功能选能力，不提及或模仿作者；不迁移小说人物、情节、固定句式、价值判断与时代类型化偏见。本项目研究的是具体中译本呈现的中文组织方式，不能称作原作者本人的中文风格。

## 仓库结构与本地分析

```text
historian-writing/        可安装的 self-contained skill
analysis/                 本地提取、来源目录、无引文近读与分析脚本
analysis/output/          可提交的聚合统计；全文抽取被忽略
evals/                    正向、反向、边界与单版本冒烟评测
docs/                     方法、语料边界与路线图
sources_and_references/   本地原书，始终被 Git 忽略
```

`analysis/source_catalog.json` 以 SHA-256 匹配本地文件，公开结果只写安全 `source_id`。完整语料在场时直接运行；只有部分已登记语料在场时，增量模式会保留已有公开画像，并拒绝不完整的历史集合重算：

```powershell
& <python-with-pypdf> .\analysis\analyze_corpus.py
& <python> .\analysis\select_close_reading.py

& <python> .\analysis\analyze_corpus.py --incremental
& <python> .\analysis\select_close_reading.py --incremental
```

全文始终只写入 `analysis/output/raw/`。公开画像保留 `cambridge_china`、`toynbee`、`historical_combined`、`anna_translation` 与 `balzac_translation`；不存在跨历史—文学语料的总体 `combined`。

## 验收

```powershell
& <python> .\evals\validate_evals.py
& <python> .\analysis\validate_project.py
& <python> <skill-creator>\scripts\quick_validate.py .\historian-writing
```

结构验证不等于效果证明。当前新增社会肌理输出仅做单版本冒烟，不能声称相对未启用 skill 的比较优势；下一步仍需匿名化真实任务的多轮盲序对照。见 [方法](docs/methodology.md)、[语料边界](docs/corpus-boundaries.md) 与 [路线图](docs/roadmap.md)。
