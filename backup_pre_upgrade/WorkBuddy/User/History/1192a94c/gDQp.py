#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Debug: 模拟 300308.SZ 的 API 返回文本，验证解析器行为"""
import os, json, re, subprocess, sys

os.environ['PYTHONIOENCODING'] = 'utf-8'

# Step 1: 获取 API 原始文本
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
m2 = re.search(r'\{[\s\S]*\}', raw)
data = json.loads(m2.group())
recalls = data['data']['apiData']['apiRecall']

all_content = "\n".join(r.get("content", "") for r in recalls)
print("总文本长度: {} 字符".format(len(all_content)))
print("API 返回块数: {}".format(len(recalls)))
print()

# 模拟 _split
def _classify(c):
    if not c:
        return "unknown"
    if re.search(r'\u5e74\u62a5|\u5e74\u5ea6\u62a5\u544a|\u5168\u5e74', c):
        return "annual"
    return "unknown"

def norm_date(d):
    d = d.replace('\u5e74', '').replace('\u6708', '').replace('\u65e5', '').replace('/', '').replace('-', '').replace('\u5e74\u5ea6', '')
    if len(d) == 4 and d.isdigit():
        return d + '1231'
    if len(d) == 8 and d.isdigit():
        return d
    return None

parts = re.split(r'(\d{4}[-/\u5e74]?(?:\d{1,2}[-/\u6708]?\d{1,2}[\u65e5\u53f7]?)?)', all_content)
combined = []
i = 0
while i < len(parts) - 1:
    ds = parts[i]
    ct = parts[i+1] if i+1 < len(parts) else ""
    date_str = ds.strip()
    if re.match(r'\d{4}', date_str):
        n = norm_date(date_str)
        if n:
            combined.append({"date": n, "content": ct, "type": _classify(ct)})
    i += 2

if len(combined) < 1:
    combined = [{"date": None, "content": all_content, "type": "unknown"}]

print("解析出 {} 个段落:".format(len(combined)))
for idx, seg in enumerate(combined):
    print("  [{}] date={}, type={}, content_len={}".format(idx, seg['date'], seg['type'], len(seg['content'])))
    preview = seg['content'][:200].replace('\n', ' ')
    print("       preview: {}...".format(preview))
print()

# 找 latest annual
cand = [s for s in combined if s["type"] == "annual" and s["date"]]
if cand:
    cand.sort(key=lambda x: x["date"], reverse=True)
    a = cand[0]
    print("选中段落: date={}, content_len={}".format(a['date'], len(a['content'])))
    print("--- 段落内容 ---")
    print(a['content'][:3000])
    print("--- 结束 ---")
    print()
    
    c = a['content']
    
    # OCF
    ocf_pat = r'\u7ecf\u8425\u6d3b\u52a8.*\u73b0\u91d1\u6d41\u91cf\u51c0\u989d\s*([-+]?\d+\.?\d*)\s*(?\u4e07[\u4ebf]?\u5143|\u4ebf\u5143|\u4e07\u5143|\u4e07\u4ebf\u5143|\u5343\u5143|\u5143)'
    ocf_m = re.search(ocf_pat, c)
    if ocf_m:
        print("OCF 匹配成功: {}".format(ocf_m.group(0)[:80]))
    else:
        print("OCF 未匹配!")
        for kw in ['\u7ecf\u8425\u6d3b\u52a8', '\u73b0\u91d1\u6d41\u91cf', '\u73b0\u91d1\u6d41']:
            if kw in c:
                p = c.index(kw)
                print("  找到 '{}' 在 {}: ...{}...".format(kw, p, c[max(0,p-10):p+100]))
    
    # 净利润
    np_pat = r'\u51c0\u5229\u6da6\s*([-+]?\d+\.?\d*)\s*(?\u4e07[\u4ebf]?\u5143|\u4ebf\u5143|\u4e07\u5143|\u4e07\u4ebf\u5143|\u5343\u5143|\u5143)'
    np_m = re.search(np_pat, c)
    if np_m:
        print("净利润匹配成功: {}".format(np_m.group(0)[:80]))
    else:
        print("净利润未匹配!")
        if '\u51c0\u5229\u6da6' in c:
            p = c.index('\u51c0\u5229\u6da6')
            print("  找到 '净利润' 在 {}: ...{}...".format(p, c[max(0,p-10):p+100]))
    
    # 毛利率
    gm_pats = [
        r'\u9500\u552e\u6bdb\u5229\u7387[：:=\s]*([-+]?\d+\.?\d*)%',
        r'\u6bdb\u5229\u7387[：:=\s]*([-+]?\d+\.?\d*)%',
    ]
    gm_val = None
    for gp in gm_pats:
        m3 = re.search(gp, c)
        if m3:
            gm_val = float(m3.group(1))
            break
    if gm_val is None:
        all_pcts = re.findall(r'(?<![0-9])([-+]?\d+\.?\d*)%', c)
        if all_pcts:
            gm_val = float(all_pcts[-1])
    print("毛利率: {}".format(gm_val))
    
    # 净利率
    nm_pats = [
        r'\u9500\u552e\u51c0\u5229\u7387[：:=\s]*([-+]?\d+\.?\d*)%',
        r'\u51c0\u5229\u7387[：:=\s]*([-+]?\d+\.?\d*)%',
    ]
    nm_val = None
    for np2 in nm_pats:
        m4 = re.search(np2, c)
        if m4:
            nm_val = float(m4.group(1))
            break
    print("净利率: {}".format(nm_val))
    
    # 营收同比
    ry_pats = [
        r'\u8425\u4e1a\u6536\u5165\u540c\u6bd4\u589e\u957f[：:=\s]*([-+]?\d+\.?\d*)%',
        r'\u8425\u6536\u540c\u6bd4\u589e\u957f[：:=\s]*([-+]?\d+\.?\d*)%',
    ]
    ry_val = None
    for rp in ry_pats:
        m5 = re.search(rp, c)
        if m5:
            ry_val = float(m5.group(1))
            break
    print("营收同比: {}".format(ry_val))
    
    # 净利润同比
    py_pats = [
        r'\u51c0\u5229\u6da6\u540c\u6bd4\u589e\u957f[：:=\s]*([-+]?\d+\.?\d*)%',
        r'\u5f52\u6bcd\u51c0\u5229\u6da6\u540c\u6bd4\u589e\u957f[：:=\s]*([-+]?\d+\.?\d*)%',
    ]
    py_val = None
    for pp in py_pats:
        m6 = re.search(pp, c)
        if m6:
            py_val = float(m6.group(1))
            break
    print("净利润同比: {}".format(py_val))
    
    # 资产负债率
    dr_pats = [
        r'\u8d44\u4ea7\u8d1f\u503a\u7387[：:=\s]*([-+]?\d+\.?\d*)%',
        r'\u8d1f\u503a\u7387[：:=\s]*([-+]?\d+\.?\d*)%',
    ]
    dr_val = None
    for dp in dr_pats:
        m7 = re.search(dp, c)
        if m7:
            dr_val = float(m7.group(1))
            break
    print("资产负债率: {}".format(dr_val))
    
    # ROE
    roe_pats = [
        r'\u52a0\u6743\u51c0\u8d44\u4ea7\u6536\u76ca\u7387ROE[：:=\s]*([-+]?\d+\.?\d*)%',
        r'\u51c0\u8d44\u4ea7\u6536\u76ca\u7387[：:=\s]*([-+]?\d+\.?\d*)%',
        r'ROE[：:=\s]*([-+]?\d+\.?\d*)%',
    ]
    roe_val = None
    for rp2 in roe_pats:
        m8 = re.search(rp2, c)
        if m8:
            roe_val = float(m8.group(1))
            break
    print("ROE: {}".format(roe_val))

else:
    print("未找到任何 annual 类型段落!")
    print("所有段落类型:", [s["type"] for s in combined])
