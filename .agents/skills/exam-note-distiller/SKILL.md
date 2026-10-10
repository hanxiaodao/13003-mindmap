---
name: exam-note-distiller
description: 考试导向的课程考点笔记蒸馏 + 交互式思维导图生成。当用户想整理某门课的考点笔记/复习笔记、分析历年真题、从教材提炼考点、把课程知识点做成思维导图或知识点网页时使用——即用户说"帮我把这门课整理成考点笔记""做个思维导图""分析真题""提炼考点""考前笔记"之类的话，即使用户没提"考试"两个字，只要目标是从课程资料产出高密度复习笔记，就用本 skill。流程：真题反推考点 → 考点聚类评级 → 教材/个人笔记/网络补齐 → 产出 exam-notes.md → 按模板渲染交互式 HTML。PDF 素材经 MinerU 解析。
---

# Exam Note Distiller

把历年真题 + 教材（+ 考试大纲 + 个人笔记）蒸馏成一份**以考试为中心的高密度考点笔记**，并渲染成交互式 HTML 思维导图（暗/亮主题、折叠章节、考点评级徽章、一键导出 Markdown）。

核心立场：**从真题反推这门课怎么考，再回教材补齐所需知识。** 不做"教材复读机"。

skill 内置三个脚本：MinerU PDF 解析（parse_pdf.py）、docx 本地转换（docx2md.py，MinerU 降级路径）、渲染器（render_notes.py，exam-notes.md → index.html 的权威实现）。**渲染一律跑脚本，不要 AI 现场手写 HTML**（原因见 Phase 6）。

## 红线（违反即返工）

1. **禁止编造真题证据。** 年份、题号、考查内容只能来自用户提供的材料；记不清写【待核实】。
2. **禁止伪造趋势。** 样本不足不下趋势结论；表述用"近年出现……"，不用"以后一定……"。
3. **禁止把网络知识或个人笔记内容包装成教材原文、大纲要求。**
4. **"没考过"≠"超纲"。** 只有大纲支持才能标非重点，否则标【低频】保留。

## 工作目录与产物

在用户指定的课程目录（没有就建一个）内工作：

```
<课程目录>/
├── materials/          # 用户提供的原始素材：真题、教材、大纲、个人笔记
│   └── parsed/         # PDF 经 MinerU 解析后的 Markdown（parse_pdf.py 输出）
├── distill/
│   ├── papers.md       # 真题拆解记录（每题一条）
│   ├── topics.md       # 考点登记表（聚类结果+频率+评级）
│   └── coverage.md     # 覆盖矩阵（真题 × 考点）
├── exam-notes.md       # 最终笔记（唯一内容源，规范见 references/format-contract.md）
└── index.html          # 渲染产物（scripts/render_notes.py 生成）
```

中间文件必须落盘，大课程跨多轮会话时靠它们续作。**exam-notes.md 是唯一内容源**：后续任何内容修改先改它，再重新渲染 HTML；不要直接在 HTML 上改内容。

## 流程

### Phase 0 · 素材盘点

问清（能从上下文判断的不要问）：哪门课；材料有哪些——**真题（几套、有没有答案）、教材、大纲、个人总结的笔记**；哪些是 PDF；要不要渲染成网页。

然后按 references/distillation-guide.md §2 的降级路径确定模式（真题充足 / 真题少 / 无真题纯大纲模式）——**这决定后面评级和趋势结论能做多细**。

### Phase 1 · 素材预处理

- **PDF 素材**（教材章节、真题扫描件、课件）：先跑 MinerU 解析，输出到 `materials/parsed/`：

  ```bash
  MINERU_API_KEY=<key> python <skill目录>/scripts/parse_pdf.py 教材.pdf 真题.pdf -o materials/parsed
  ```

  key 由用户配置在环境变量 `MINERU_API_KEY`；未配置就向用户要，不要猜测。扫描件加 `--ocr`。**解析结果是机器识别的，公式和表格要先抽查再当内容依据**；识别质量差的部分向用户说明，必要时请用户提供可复制文本。

- **docx 素材**：MinerU 只收 PDF 且单文件 ≤200 页，教材 docx（尤其大部头）直接传会失败。降级路径：本地解包转换——`python <skill目录>/scripts/docx2md.py 教材.docx -o materials/parsed/教材.md`（docx 即 zip+XML，标题按 pStyle 层级还原；代码块识别按 C++ 教材特征，其他学科只是少识别代码块，不损坏文本）。

- **个人笔记**：通读后按类型归档——口诀/记忆技巧、易错记录、自己的理解与扩展。它们稍后融入对应考点（人话解释、tip 块），并反映用户的薄弱环节（相关考点可适当加重）。个人笔记与教材/真题冲突时按 distillation-guide.md §13 处理，并向用户指出。

### Phase 2 · 真题拆解

逐题拆解写入 `distill/papers.md`（字段见 distillation-guide.md §3）。批量进行：每读完一套真题就落盘一次。

### Phase 3 · 考点聚类与评级

按"共同知识结构"把题聚成考点（题 ≠ 考点），按四相似聚类、不按教材章节；统计频率、评级 S–D，写入 `distill/topics.md`。规则见 distillation-guide.md §4–§7。

### Phase 4 · 补齐知识

对每个考点回教材提取必需知识（深度按考法定，见 distillation-guide.md §9），融入个人笔记中对应的内容。教材缺啥补啥时用 WebSearch/WebFetch 检索，遵守 distillation-guide.md §16：关键结论两个来源一致才用，分歧标【存疑】。

### Phase 5 · 撰写 exam-notes.md

写笔记。开写前必读两份文档：

- **references/format-contract.md** — 内容格式规范（exam-notes.md 是唯一内容源，HTML 渲染以它为准）
- **references/style-guide.md** — 写作风格（考点粒度、子主题骨架、文风七条、篇幅基准）

总览层（考试地图/高频公式/高频易错/题型索引/考前速记）按 format-contract.md §4 放置。

### Phase 6 · 渲染 HTML（一律用脚本）

```bash
python <skill目录>/scripts/render_notes.py exam-notes.md      # 产出同目录 index.html
```

渲染规则（token 替换表、内容块 → CSS 类的映射、章节配色表）写在 **assets/template.html** 文件头注释里，脚本是它的权威实现。模板自带完整交互：折叠、主题切换、Markdown 导出、"展开全部/收起全部"工具条、整页搜索（Ctrl+K，含折叠内容与页内高亮）、回到顶部悬浮组、front matter 驱动的右上角胶囊入口。**不要让 AI 现场手写渲染**——04737 项目里手写连续踩了 4 个坑，现已全部固化进脚本并在代码里注明原因：

1. 模板头部"使用说明注释"里也含 `@@TOKEN@@` 字样 → 必须只在 `-->` 之后替换，否则内容注进注释里、整文件损坏；
2. 考点 meta 行先删后解析 → level/freq 徽章全部消失；
3. 考点没包进 `<div class="ch-body">` → 章节折叠时考点仍然可见；
4. 模板 JS 只绑 keydown → 生成的章/考点标题必须带 `onclick="toggleCh(this)"/"toggleKp(this)"`，否则鼠标点不动。

front matter 的 `github:` 点亮仓库按钮；`quiz:`/`mistakes:` 生成右上角"刷题"/"错题集"固定胶囊入口（见 format-contract.md §1）。

### Phase 7 · 验证（不验证不算完成）

1. **渲染目检**：浏览器打开 index.html，展开两三个章节，检查公式块、表格、徽章、深浅主题。浏览器截图/打开通道不可用时，**降级为 DOM 统计核验**：章数、考点数、level 徽章数、公式/提示框/表格计数与 exam-notes.md 对账，折叠交互点一次验证——并向用户如实说明"未做目检，只做了统计核验"。
2. **真题回测**：按 distillation-guide.md §17 执行四问回测，写 `distill/coverage.md` 覆盖矩阵，跑完自检六问。
3. 向用户报告：章数/考点数/评级分布，以及回测发现的缺口与处理方式。

### 更新已有笔记

用户后续说"补充/修改某个考点""把新一份真题并进来"时：先改 `exam-notes.md`（必要时同步更新 distill/ 的拆解与登记），再重跑 render_notes.py 重新渲染（整文件重渲成本极低），最后目检或统计核验。不要从头重写没变的部分。

两条迭代纪律（来自 04737 项目的 39→53→55 考点三次迭代）：

- **考点编号只追加、不重排。** 编号被 coverage.md 的真题映射矩阵和正文交叉引用（"见考点34"）钉死，中间插号重排会全线失配。新考点追加到所属章末尾即可。
- **用户嫌"考点太少"时先做三方覆盖审计**，再决定加什么：① 大纲逐条考核要求 × ② 参考笔记专节 × ③ 现有考点。大纲有条目而笔记只有一句带过的做"充实"；教材正文/附录独有、与已有考点强相关的可立新考点（如实标注"未单独出题"）；参考笔记独有、大纲无考核条目、真题也没考过的（枚举、优先级全表之类）不收，避免稀释考点密度。

## 参考文档索引

| 文件 | 什么时候读 |
|---|---|
| references/distillation-guide.md | Phase 0–4、7：方法论、降级路径、检索规则、验证闭环 |
| references/format-contract.md | Phase 5 开写前：exam-notes.md 的格式契约（含 front matter 指令表） |
| references/style-guide.md | Phase 5 开写前：考点结构与文风 |
| assets/template.html | 想理解渲染规则时：模板 + 文件头注释（渲染由脚本完成，通常不必读） |
| scripts/parse_pdf.py | Phase 1：PDF/扫描件 → Markdown（MinerU，需 MINERU_API_KEY） |
| scripts/docx2md.py | Phase 1：素材是 docx 或超 200 页时的本地转换（MinerU 降级路径） |
| scripts/render_notes.py | Phase 6 及一切重新渲染：exam-notes.md → index.html 的权威渲染器 |

## 收尾建议

渲染完成后，如果用户想发布，提示可选：把 `<课程目录>/index.html` 与 `exam-notes.md` 放入一个 git 仓库推送到 GitHub Pages（或复用用户已有的 mindmap 仓库模式）。不要主动 push。发布前可在 front matter 里把 `github:` 填成仓库地址（页面上出现仓库按钮）、`quiz:`/`mistakes:` 挂上配套的刷题/错题集网址；Pages 在仓库 Settings 里选 main 分支根目录即可（开启 Pages 需要仓库管理员权限，协作者不够）。
