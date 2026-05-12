#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os, json, re, subprocess, sys
os.environ['PYTHONIOENCODING'] = 'utf-8'

cmd = [
    sys.executable, '-X', 'utf8',
    r'C:\Users\green\.workbuddy\plugins\marketplaces\cb_teams_marketplace\plugins\finance-data\skills\neodata-financial-search\scripts\query.py',
    '--query', '300308.SZ 中际旭创 年报',
    '--data-type', 'api'
]
result = subprocess.run(cmd, capture_output=True)
raw = result.stdout.decode('utf-8', errors='replace')
raw = re.sub(r'#< CLIXML\r?\n?', '', raw)
raw = re.sub(r'<Objs[\s\S]*?</Objs>', '', raw)
m = re.search(r'\{[\s\S]*\}', raw)
data = json.loads(m.group())
recalls = data['data']['apiData']['apiRecall']
all_content = "\n".join(r.get("content", "") for r in recalls)

# 手动执行 _split 逻辑
def _norm(d):
    d = d.replace('\u5e74', '').replace('\u6708', '').replace('\u65e5', '').replace('/', '').replace('-', '').replace('\u5e74\u5ea6', '')
    if len(d) == 4 and d.isdigit():
        return d + '1231'
    if len(d) == 8 and d.isdigit():
        return d
    return None

# 扫描年报日期
print("=== 扫描年报关键词 ===")
annual_dates = set()
pat1 = r'(\d{4}[-/\u5e74]?(?:\d{1,2}[-/\u6708]?\d{1,2}[\u65e5\u53f7]?)?)\s*\u7684?\s*(?:\u5e74\u62a5|\u5e74\u5ea6\u62a5\u544a|\u5168\u5e74)'
for m in re.finditer(pat1, all_content):
    raw_d = m.group(1)
    n = _norm(raw_d)
    print("  匹配1: raw={} norm={} 完整匹配={}".format(repr(raw_d), n, repr(m.group(0)[:80])))
    if n:
        annual_dates.add(n)

pat2 = r'(\d{4})\s*\u5e74?\s*(?:\u5e74\u62a5|\u5e74\u5ea6\u62a5\u544a|\u5168\u5e74)'
for m in re.finditer(pat2, all_content):
    raw_d = m.group(1)
    n = _norm(raw_d)
    print("  匹配2: raw={} norm={} 完整匹配={}".format(repr(raw_d), n, repr(m.group(0)[:80])))
    if n:
        annual_dates.add(n)

print("annual_dates = {}".format(annual_dates))
print()

# 显示 API 文本中所有包含"年报"的位置
print("=== 所有'年报'关键词位置 ===")
for m in re.finditer(r'\u5e74\u62a5', all_content):
    pos = m.start()
    ctx = all_content[max(0,pos-60):pos+60].replace('\n', ' ')
    print("  位置 {}: ...{}...".format(pos, ctx))
print()

# 显示所有日期
print("=== 所有日期匹配 ===")
date_pat = r'\d{4}[-/\u5e74]?(?:\d{1,2}[-/\u6708]?\d{1,2}[\u65e5\u53f号]?'
for m in re.finditer(date_pat, all_content):
    pos = m.start()
    ctx = all_content[max(0,pos-30):pos+50].replace('\n', ' ')
    print("  {} 位置{}: ...{}...".format(m.group(), pos, ctx))
