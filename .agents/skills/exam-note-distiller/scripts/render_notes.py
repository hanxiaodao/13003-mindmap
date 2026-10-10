# -*- coding: utf-8 -*-
"""exam-notes.md → index.html 渲染器（按 assets/template.html 头部规则实现）。

exam-notes.md 是唯一内容源；内容修改后重跑本脚本即可，不要直接改 index.html，
也不要让 AI 现场手写渲染——手写已知的坑（脚本内都已处理）：

1. 模板头部"使用说明注释"里也含 @@TOKEN@@ 字样，必须只在 '-->' 之后做替换，
   否则章节会被注进注释里，文件损坏。
2. 考点 meta 行要先解析再从 body 里过滤掉，顺序反了徽章（S/A/B/C/D 与频率）会消失。
3. 每章的考点必须包进 <div class="ch-body">，否则章节折叠时考点仍然可见。
4. 模板 JS 只给章/考点标题绑了 keydown，鼠标点击靠生成的
   onclick="toggleCh(this)"/"toggleKp(this)" 属性，漏了就只能键盘操作。
5. 右上角胶囊入口（quiz:/mistakes:）用 position:fixed 悬浮，坐标要避开
   模板自身的导出/主题/GitHub 按钮（见 build_corner 内 CSS 注释）。

用法：
  python render_notes.py [exam-notes.md] [-t 模板.html] [-o index.html]
"""
import argparse
import html
import re
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent

PALETTE = [  # (暗色, 亮色)
    ('#60a5fa', '#2563eb'), ('#34d399', '#059669'), ('#fbbf24', '#d97706'),
    ('#f472b6', '#db2777'), ('#a78bfa', '#7c3aed'), ('#22d3ee', '#0891b2'),
    ('#fb923c', '#ea580c'), ('#a3e635', '#65a30d'), ('#fb7185', '#e11d48'),
    ('#4ade80', '#16a34a'), ('#e879f9', '#a21caf'), ('#facc15', '#a16207'),
]

def chapter_color(idx):
    if idx < len(PALETTE):
        return PALETTE[idx]
    n = idx
    hue = (217 + n * 137.5) % 360
    return (f'hsl({hue:.0f},70%,62%)', f'hsl({hue:.0f},78%,38%)')

def inline(s):
    s = html.escape(s, quote=False)
    s = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', s)
    s = re.sub(r'==(.+?)==', r'<span class="em">\1</span>', s)
    return s

def render_blocks(lines):
    """内容行列表 → HTML 片段（公式/提示块/表格/列表/普通行）。"""
    out, i, n = [], 0, len(lines)
    while i < n:
        line = lines[i]
        stripped = line.strip()
        if not stripped:
            i += 1
            continue
        if stripped.startswith('```'):
            kind = stripped[3:].strip()  # f / err / tip / ok / ''
            buf, i = [], i + 1
            while i < n and not lines[i].strip().startswith('```'):
                buf.append(lines[i])
                i += 1
            i += 1  # 跳过结束 ```
            body = '\n'.join(html.escape(l, quote=False) for l in buf)
            if kind in ('err', 'tip', 'ok'):
                out.append(f'<span class="callout {kind}">{body}</span>')
            else:
                out.append(f'<span class="formula">{body}</span>')
            continue
        if stripped.startswith('|'):
            rows, i = [], i
            while i < n and lines[i].strip().startswith('|'):
                cells = [c.strip() for c in lines[i].strip().strip('|').split('|')]
                rows.append(cells)
                i += 1
            if len(rows) >= 2:  # 第二行是分隔行
                rows.pop(1)
            t = ['<table><tr>' + ''.join(f'<th>{inline(c)}</th>' for c in rows[0]) + '</tr>']
            for r in rows[1:]:
                t.append('<tr>' + ''.join(f'<td>{inline(c)}</td>' for c in r) + '</tr>')
            t.append('</table>')
            out.append(''.join(t))
            continue
        if stripped.startswith('- '):
            items, i = [], i
            while i < n and lines[i].strip().startswith('- '):
                items.append(lines[i].strip()[2:])
                i += 1
            out.append('<ul>' + ''.join(f'<li>{inline(x)}</li>' for x in items) + '</ul>')
            continue
        out.append(inline(stripped) + '<br>')
        i += 1
    return '\n'.join(out)

def parse_notes(path):
    text = open(path, encoding='utf-8').read()
    lines = text.split('\n')
    # 文件头指令
    meta_front, i = {}, 0
    while i < len(lines) and not lines[i].startswith('## '):
        m = re.match(r'^(\w+):\s*(.*)$', lines[i])
        if m:
            meta_front[m.group(1)] = m.group(2).strip()
        i += 1
    # 分章
    chapters = []
    cur = None
    for line in lines[i:]:
        if line.startswith('## '):
            cur = {'title': line[3:].strip(), 'intro': [], 'kps': [], 'buf': None}
            chapters.append(cur)
            continue
        if cur is None:
            continue
        if line.startswith('### '):
            cur['buf'] = {'title': line[4:].strip(), 'meta': {}, 'body': []}
            cur['kps'].append(cur['buf'])
            continue
        if line.startswith('#### '):
            if cur['buf'] is not None:
                cur['buf']['body'].append(('sub', line[5:].strip()))
            else:
                cur['intro'].append(('sub', line[5:].strip()))
            continue
        target = cur['buf']['body'] if cur['buf'] is not None else cur['intro']
        if line.strip():
            target.append(('line', line.rstrip()))
    # 考点 meta（先解析后过滤，避免把 meta 行删掉才找——顺序反了徽章会丢）
    for ch in chapters:
        for kp in ch['kps']:
            for kind, val in kp['body']:
                m = re.match(r'^meta:\s*level=(\w+)?;\s*freq=(.*)$', val.strip())
                if m:
                    kp['meta'] = {'level': m.group(1) or '', 'freq': m.group(2).strip()}
                    break
            kp['body'] = [b for b in kp['body'] if not (b[0] == 'line' and b[1].strip().startswith('meta:'))]
    return meta_front, chapters

def build_chapters(chapters):
    parts = []
    for idx, ch in enumerate(chapters):
        dark, light = chapter_color(idx)
        badge = f'<span class="badge">{len(ch["kps"])}考点</span>' if ch['kps'] else ''
        p = [f'<div class="ch" style="--accent:{dark};--accent-light:{light}">']
        p.append(f'<div class="ch-title" role="button" tabindex="0" aria-expanded="false" onclick="toggleCh(this)">'
                 f'<span class="ch-title-text">{inline(ch["title"])}{badge}</span>'
                 f'<span class="arrow">▼</span></div>')
        body = ['<div class="ch-body">']
        if ch['intro']:
            body.append('<div class="ch-intro">' + render_blocks([b[1] for b in ch['intro']]) + '</div>')
        for kp in ch['kps']:
            m = re.match(r'^考点(\d+)[：:]\s*(.*)$', kp['title'])
            num, name = (f'考点{m.group(1)}', m.group(2)) if m else ('', kp['title'])
            level = kp['meta'].get('level', '')
            lv = f'<span class="kp-level lv-{level}">{level}</span>' if level else ''
            freq = kp['meta'].get('freq', '')
            fq = f'<span class="kp-freq">{inline(freq)}</span>' if freq else ''
            body.append('<div class="kp">')
            body.append(f'<div class="kp-title" role="button" tabindex="0" aria-expanded="false" onclick="toggleKp(this)">'
                        f'<span class="kp-num">{num}</span><span class="kp-name">{inline(name)}</span>'
                        f'{lv}{fq}<span class="kp-arrow">▼</span></div>')
            body.append('<div class="kp-detail">' + render_blocks([b[1] for b in kp['body']]) + '</div>')
            body.append('</div>')
        body.append('</div>')
        p.extend(body)
        p.append('</div>')
        parts.append('\n'.join(p))
    return '\n\n'.join(parts)

def build_corner(front):
    """右上角固定入口胶囊组（仿 02324 站点的错题本入口）。
    front matter 里 quiz:/mistakes: 有值就各生成一枚，方便以后追加。
    坐标依据本模板：桌面端导出/主题按钮占 right:64~112px，GitHub（若启用）占 right:16px，
    故胶囊组桌面放 right:160px；移动端 no-github 时按钮最左到 52+36=88px，故放 right:96px。"""
    items = (('quiz', '刷题',
              '<path d="M12 20h9"/><path d="M16.5 3.5a2.12 2.12 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z"/>'),
             ('mistakes', '错题集',
              '<path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/>'))
    css = ('<style>'
           '.corner-links{position:fixed;top:16px;right:160px;display:flex;gap:8px;z-index:100;}'
           '.corner-link{height:38px;border-radius:19px;border:1px solid var(--border);'
           'background:var(--surface);color:var(--muted);display:flex;align-items:center;gap:6px;'
           'padding:0 13px;font-size:12.5px;text-decoration:none;transition:color .15s,border-color .15s;}'
           '.corner-link:hover{color:var(--heading);border-color:var(--border-strong);}'
           '.corner-link:focus-visible{outline:2px solid var(--border-strong);outline-offset:2px;}'
           '@media (max-width:600px){.corner-links{top:10px;right:96px;}'
           '.corner-link{height:36px;padding:0 11px;}}'
           '</style>')
    links = []
    for key, label, icon in items:
        url = front.get(key, '')
        if url:
            links.append(f'<a class="corner-link" href="{url}" target="_blank" rel="noopener" '
                         f'aria-label="{label}" title="{label}">'
                         f'<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
                         f'stroke-width="2" stroke-linecap="round" stroke-linejoin="round" '
                         f'aria-hidden="true">{icon}</svg>{label}</a>')
    if not links:
        return ''
    return css + '<div class="corner-links">' + ''.join(links) + '</div>'

def main():
    ap = argparse.ArgumentParser(description='exam-notes.md → index.html')
    ap.add_argument('notes', nargs='?', default='exam-notes.md', help='笔记源文件（默认 exam-notes.md）')
    ap.add_argument('-t', '--template', default=str(SKILL_DIR / 'assets' / 'template.html'))
    ap.add_argument('-o', '--out', default=None, help='输出文件（默认与笔记同目录 index.html）')
    args = ap.parse_args()
    out_path = args.out or str(Path(args.notes).resolve().parent / 'index.html')
    front, chapters = parse_notes(args.notes)
    tpl = open(args.template, encoding='utf-8').read()
    # 坑：模板头部使用说明注释里也含 @@TOKEN@@ 字样，只在注释结束后做替换
    comment_end = tpl.index('-->') + 3
    head, body = tpl[:comment_end], tpl[comment_end:]
    course = front.get('course', '考点笔记')
    subtitle = front.get('subtitle', '')
    kp_total = sum(len(c['kps']) for c in chapters)
    sub_stat = ''
    if subtitle:
        sub_stat = f'<div class="header-divider"></div><div class="header-stat"><strong>{inline(subtitle)}</strong></div>'
    export_name = course.replace(' ', '') + '考点笔记.md'
    out = head + (body
           .replace('@@PAGE_TITLE@@', inline(course) + ' · 考点笔记')
           .replace('@@H1@@', inline(course))
           .replace('@@STAT_CH@@', str(len(chapters)))
           .replace('@@STAT_KP@@', str(kp_total))
           .replace('@@SUBTITLE_STAT@@', sub_stat)
           .replace('@@BODY_CLASS@@', 'no-github' if not front.get('github') else '')
           .replace('@@GITHUB@@', front.get('github', '#'))
           .replace('@@EXPORT_NAME@@', export_name)
           .replace('@@CHAPTERS@@', build_corner(front) + build_chapters(chapters)))
    open(out_path, 'w', encoding='utf-8').write(out)
    print(f'OK {out_path}: {len(chapters)} 章, {kp_total} 考点')

if __name__ == '__main__':
    main()
