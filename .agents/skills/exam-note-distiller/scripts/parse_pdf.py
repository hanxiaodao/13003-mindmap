#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MinerU 在线 API · PDF/DOCX/PPT → Markdown 解析

把课程素材（教材、真题扫描件、课件）交给 mineru.net 解析，
下载结果 ZIP 并展开为 Markdown + images/。

用法:
  python parse_pdf.py 教材.pdf 真题2024.pdf          # 输出到 ./parsed/<文件名>/
  python parse_pdf.py 教材.pdf -o materials/parsed --ocr

环境变量:
  MINERU_API_KEY   必填。mineru.net → 个人中心 → API 管理 → 创建 Token

说明:
  - 走 v4 批量接口（申请上传链接 → PUT 上传 → 轮询 → 下载 ZIP）
  - 单文件 ≤ 200MB、≤ 200 页；公式/表格识别默认开启
  - 扫描件/图片版加 --ocr
  - 结果里 full.md 是正文，images/ 是其中引用的图片；layout/model 等 JSON 为调试数据可忽略
"""

import argparse
import io
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import zipfile

API = 'https://mineru.net/api/v4'
POLL_INTERVAL = 10


def http_json(url, key, payload=None, method=None, timeout=60):
    req = urllib.request.Request(url, method=method)
    req.add_header('Authorization', f'Bearer {key}')
    if payload is not None:
        req.add_header('Content-Type', 'application/json')
        data = json.dumps(payload).encode('utf-8')
    else:
        data = None
    with urllib.request.urlopen(req, data=data, timeout=timeout) as resp:
        return json.loads(resp.read().decode('utf-8'))


def http_put(url, path):
    # 官方要求：PUT 上传不带 Content-Type 头。
    # urllib 对带 body 的请求会默认加 Content-Type，破坏 OSS 预签名签名（403），
    # 因此用 http.client 直传（只加 Content-Length）。
    import http.client
    with open(path, 'rb') as f:
        data = f.read()
    p = urllib.parse.urlsplit(url)
    conn = http.client.HTTPSConnection(p.netloc, timeout=300)
    try:
        conn.request('PUT', urllib.parse.urlunsplit(('', '', p.path, p.query, '')),
                     body=data)
        resp = conn.getresponse()
        status = resp.status
        resp.read()
    finally:
        conn.close()
    if status not in (200, 204):
        raise RuntimeError(f'上传失败 HTTP {status}')


def download(url, timeout=300):
    with urllib.request.urlopen(url, timeout=timeout) as resp:
        return resp.read()


def unzip_to(data, dest):
    os.makedirs(dest, exist_ok=True)
    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        for info in zf.infolist():
            name = info.filename.replace('\\', '/')
            if name.startswith('/') or '..' in name:
                continue  # 跳过路径可疑的条目
            target = os.path.join(dest, *name.split('/'))
            if info.is_dir():
                os.makedirs(target, exist_ok=True)
                continue
            os.makedirs(os.path.dirname(target) or dest, exist_ok=True)
            with open(target, 'wb') as f:
                f.write(zf.read(info))


def main():
    ap = argparse.ArgumentParser(description='MinerU 批量解析 PDF → Markdown')
    ap.add_argument('files', nargs='+', help='PDF/DOCX/PPTX 等本地文件')
    ap.add_argument('-o', '--outdir', default='parsed', help='输出根目录（默认 ./parsed）')
    ap.add_argument('--ocr', action='store_true', help='扫描件/图片版开启 OCR')
    ap.add_argument('--model', default='pipeline', choices=['pipeline', 'vlm'],
                    help='解析模型：pipeline(默认) 或 vlm(版面更复杂时)')
    ap.add_argument('--lang', default='ch', help='文档语言（默认 ch）')
    ap.add_argument('--timeout', type=int, default=900, help='轮询超时秒数（默认 900）')
    args = ap.parse_args()

    key = os.environ.get('MINERU_API_KEY')
    if not key:
        sys.exit('❌ 未设置 MINERU_API_KEY 环境变量。到 mineru.net → API 管理 创建 Token 后：\n'
                 '   PowerShell:  $env:MINERU_API_KEY = "..." \n'
                 '   Git Bash:    export MINERU_API_KEY="..."')

    paths = [os.path.abspath(f) for f in args.files]
    for p in paths:
        if not os.path.isfile(p):
            sys.exit(f'❌ 文件不存在: {p}')

    print(f'📤 申请上传链接（{len(paths)} 个文件，model={args.model}, ocr={args.ocr}）')
    res = http_json(f'{API}/file-urls/batch', key, payload={
        'files': [{'name': os.path.basename(p), 'data_id': os.path.splitext(os.path.basename(p))[0]}
                  for p in paths],
        'model_version': args.model,
        'language': args.lang,
        'enable_formula': True,
        'enable_table': True,
        'is_ocr': args.ocr,
    })
    if res.get('code') != 0:
        sys.exit(f'❌ 申请失败: {res.get("msg")}')
    batch_id = res['data']['batch_id']
    urls = res['data']['file_urls']
    if len(urls) != len(paths):
        sys.exit(f'❌ 上传链接数量不符: {len(urls)} vs {len(paths)}')

    for p, u in zip(paths, urls):
        print(f'⬆️  上传 {os.path.basename(p)} …')
        http_put(u, p)
    print(f'🗂  batch_id = {batch_id}，已自动提交解析')

    deadline = time.time() + args.timeout
    states = {}
    while time.time() < deadline:
        res = http_json(f'{API}/extract-results/batch/{batch_id}', key)
        if res.get('code') != 0:
            sys.exit(f'❌ 查询失败: {res.get("msg")}')
        results = res['data']['extract_result']
        states = {r['file_name']: r for r in results}
        done = [n for n, r in states.items() if r['state'] == 'done']
        failed = {n: r.get('err_msg') for n, r in states.items() if r['state'] == 'failed'}
        prog = ', '.join(
            f"{n}:{r['state']}" + (f" {r.get('extract_progress', {}).get('extracted_pages', '?')}/"
                                   f"{r.get('extract_progress', {}).get('total_pages', '?')}"
                                   if r.get('extract_progress') else '')
            for n, r in states.items())
        print(f'⏳ {prog}')
        if failed:
            for n, msg in failed.items():
                print(f'   ❌ {n}: {msg}')
        if len(done) + len(failed) == len(paths):
            break
        time.sleep(POLL_INTERVAL)
    else:
        sys.exit(f'❌ 轮询超时（{args.timeout}s）。可稍后用 batch_id 手动查询：\n'
                 f'   GET {API}/extract-results/batch/{batch_id}')

    ok = 0
    for name, r in states.items():
        if r['state'] != 'done' or not r.get('full_zip_url'):
            continue
        stem = os.path.splitext(name)[0]
        dest = os.path.join(args.outdir, stem)
        print(f'📥 下载并展开 {name} → {dest}')
        unzip_to(download(r['full_zip_url']), dest)
        md = os.path.join(dest, 'full.md')
        if os.path.isfile(md):
            size = os.path.getsize(md) / 1024
            print(f'   ✅ {md}  ({size:.0f} KB)')
            ok += 1
        else:
            print(f'   ⚠️  ZIP 中未见 full.md，请检查 {dest}')
    if ok == 0:
        sys.exit('❌ 没有成功解析的文件')
    print(f'✅ 完成 {ok}/{len(paths)}。解析结果为机器识别，公式/表格抽查后再作为内容依据。')


if __name__ == '__main__':
    main()
