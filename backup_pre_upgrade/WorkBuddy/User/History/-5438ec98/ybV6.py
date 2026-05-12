#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os, json, re, subprocess, sys
os.environ['PYTHONIOENCODING'] = 'utf-8'

cmd = [sys.executable, '-X', 'utf8',
    r'C:\Users\green\.workbuddy\plugins\marketplaces\cb_teams_marketplace\plugins\finance-data\skills\neodata-financial-search\scripts\query.py',
    '--query', '300308.SZ 中际旭创 年报', '--data-type', 'api']
result = subprocess.run(cmd, capture_output=True)
raw = result.stdout.decode('utf-8', errors='replace')
raw = re.sub(r'#< CLIXML\r?\n?', '', raw)
raw = re.sub(r'<Objs[\s\S]*?</Objs>', '', raw)
m = re.search(r'\{[\s\S]*\}', raw)
data = json.loads(m.group())
recalls = data['data']['apiData']['apiRecall']
all_content = "\n".join(r.get("content", "") for r in recalls)

# 手动执行 _split
def _norm(d):
    d = d.replace('年', '').replace('月', '').replace('日', '').replace('/', '').replace('-', '').replace('年度', '')
    if len(d) == 4 and d.isdigit():
        return d + '1231'
    if len(d) == 8 and d.isdigit():
        return d
    return None

annual_dates = set()
pat1 = r'(\d{4}[-/年]?(?:\d{1,2}[-/月]?\d{1,2}[日号]?)?)\s*的?\s*(?:年报|年度报告|全年)'
for m2 in re.finditer(pat1, all_content):
    raw_d = m2.group(1)
    n = _norm(raw_d)
    print("pat1 match: raw={} norm={}".format(repr(raw_d), n))
    if n:
        annual_dates.add(n)

pat2 = r'(\d{4})\s*年?\s*(?:年报|年度报告|全年)'
for m3 in re.finditer(pat2, all_content):
    raw_d = m3.group(1)
    n = _norm(raw_d)
    print("pat2 match: raw={} norm={}".format(repr(raw_d), n))
    if n:
        annual_dates.add(n)

print("annual_dates = {}".format(annual_dates))
print()

# split
parts = re.split(r'(\d{4}[-/年]?(?:\d{1,2}[-/月]?\d{1,2}[日号]?)?)', all_content)
print("Total parts: {}".format(len(parts)))

combined = []
i = 0
while i < len(parts) - 1:
    ds = parts[i]
    ct = parts[i+1] if i+1 < len(parts) else ""
    date_str = ds.strip()
    if re.match(r'\d{4}', date_str):
        n = _norm(date_str)
        if n:
            seg_type = "unknown"
            if n in annual_dates:
                seg_type = "annual"
            elif re.search(r'年报|年度报告|全年', ct):
                seg_type = "annual"
            combined.append({"date": n, "content": ct, "type": seg_type})
    i += 2

if len(combined) < 1:
    combined = [{"date": None, "content": all_content, "type": "unknown"}]

print("Segments:")
for idx, seg in enumerate(combined):
    print("  [{}] date={} type={} content_len={}".format(idx, seg['date'], seg['type'], len(seg['content'])))
    # 打印前100字符
    print("       {}".format(seg['content'][:100].replace('\n', ' ')))
print()

# 找 latest annual
cand = [s for s in combined if s["type"] == "annual" and s["date"]]
if cand:
    cand.sort(key=lambda x: x["date"], reverse=True)
    a = cand[0]
    print("Selected annual: date={} content_len={}".format(a['date'], len(a['content'])))
    print("Content preview: {}".format(a['content'][:500].replace('\n', ' ')))
else:
    print("No annual segment found!")
