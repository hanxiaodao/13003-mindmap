# 13003 数据结构与算法 · 考点笔记

全国自考 13003《数据结构与算法》的考点笔记 + 交互式复习页面 + 错题集。

## 在线阅读

**https://hanxiaodao.github.io/13003-mindmap/**

- [考点笔记页](https://hanxiaodao.github.io/13003-mindmap/)（index.html）：58 个考点按教材八章编号，含考点评级（S/A/B）、真题出处、公式块、易错提醒；支持章节折叠、深浅主题、`Ctrl+K` 全文搜索、导出 Markdown。
- [错题集](https://hanxiaodao.github.io/13003-mindmap/mistakes.html)（mistakes.html）：按真题卷归档，支持按章筛选、只看未掌握、复习模式（直接展开思路）；错题数据录在 `mistakes-data.js`，把错题发给 AI 总结入档、推送后页面直接可见，无需手动导入。

## 仓库内容

| 目录 | 说明 |
|---|---|
| `index.html` / `mistakes.html` | 笔记页与错题集（单文件自包含） |
| `exam-notes.md` | 笔记唯一内容源，改动后重跑渲染脚本即可更新页面 |
| `mistakes-data.js` | 错题数据源（`window.MISTAKES` 数组），由 AI 总结录入，错题集页面读取它渲染 |
| `distill/` | 真题逐题拆解（papers-*.md）、纯题目卷（questions-*.md，仅题面无答案，可打印自测）、原题清洗稿（originals/orig-*.md，题面+答案）、考点登记表（topics.md）、真题回测覆盖矩阵（coverage.md） |
| `教材/`、`真题/`、`考点笔记/` | 原始学习资料 PDF |
| `materials/parsed/` | 上述资料经 MinerU 解析出的 Markdown 与图片 |
| `.agents/` | 渲染脚本所在工具目录 |

## 本地使用

笔记页直接双击打开即可；错题集页与 `mistakes-data.js` 同目录双击也能打开（数据跟着仓库走，换设备都是在线的同一份，不依赖浏览器本地存储）。

修改内容：编辑 `exam-notes.md`（唯一内容源）后运行

```bash
python .agents/skills/exam-note-distiller/scripts/render_notes.py exam-notes.md
```

## 版权说明

仓库内的教材、历年真题与考点解析课资料版权归机械工业出版社与命题机构所有，页面笔记为个人整理的学习笔记。全部内容仅供个人学习复习使用，请勿商用或二次传播。
