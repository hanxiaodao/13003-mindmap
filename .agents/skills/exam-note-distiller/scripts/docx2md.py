# -*- coding: utf-8 -*-
"""教材 docx → Markdown 本地转换（MinerU 降级路径）。

什么时候用：素材是 docx 时 MinerU 收不了（只收 PDF），或文件超过 200 页限制。
做法：docx 是 zip + word/document.xml，直接解包抽文本；标题层级取 pStyle 里的数字。
代码块识别按 C++ 教材特征（4 空格缩进 + #include/int/class 等开头），对其他学科
只会少识别代码块，不会损坏文本。

用法：
  python docx2md.py 教材.docx [-o 输出.md]      # 不给 -o 则同名 .md
"""
import argparse
import re
import zipfile
from xml.etree import ElementTree as ET

W = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'
NS = {'w': W}

def qn(tag):
    return '{%s}%s' % (W, tag)

def para_level(p):
    ppr = p.find('w:pPr', NS)
    if ppr is None:
        return 0
    ps = ppr.find('w:pStyle', NS)
    if ps is None:
        return 0
    val = ps.get(qn('val'), '')
    m = re.match(r'(?:Heading|heading)?([1-6])$', val)
    if m:
        return int(m.group(1))
    return 0

def convert(path, out):
    with zipfile.ZipFile(path) as z:
        root = ET.fromstring(z.read('word/document.xml'))
    body = root.find('w:body', NS)
    lines = []
    in_code = False
    for p in body.iter(qn('p')):
        texts = [t.text or '' for t in p.iter(qn('t'))]
        line = ''.join(texts).rstrip()
        if not line.strip():
            continue
        lvl = para_level(p)
        if lvl:
            if in_code:
                lines.append('```')
                in_code = False
            lines.append('')
            lines.append('#' * lvl + ' ' + line.strip())
            lines.append('')
        else:
            stripped = line.strip()
            looks_code = re.match(
                r'^(#include|using|int |void |double |char |bool |class |struct |template|cout|cin|return|if |for |while |\{|\}|//)',
                stripped) and (line.startswith('    ') or line.startswith('\t'))
            if looks_code and not in_code:
                lines.append('```cpp')
                in_code = True
            elif not looks_code and in_code and len(lines) > 0:
                lines.append('```')
                in_code = False
            lines.append(line if in_code else line)
    if in_code:
        lines.append('```')
    with open(out, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))
    print(out, '->', len(lines), 'lines')

def main():
    ap = argparse.ArgumentParser(description='docx → Markdown 本地转换')
    ap.add_argument('docx', nargs='+', help='一个或多个 docx 文件')
    ap.add_argument('-o', '--out', default=None, help='输出文件（仅单文件时可用；默认同名 .md）')
    args = ap.parse_args()
    if args.out and len(args.docx) > 1:
        ap.error('-o 只能配合单个输入文件')
    for path in args.docx:
        out = args.out or re.sub(r'\.docx$', '', path) + '.md'
        convert(path, out)

if __name__ == '__main__':
    main()
