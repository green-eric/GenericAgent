#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
深入检查：为什么中国能建和弘业期货的净利润同比不匹配
"""
import os, re, json, sys, io, requests
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

_ND_TOKEN_FILE = os.path.join(os.path.expanduser("~"), ".workbuddy", ".neodata_token")
_ND_ENDPOINT = "https://copilot.tencent.com/agenttool/v1/neodata"

def read_token():
    try:
        with open(_ND_TOKEN_FILE, 'r') as f:
            t = f.read().strip()
            if t: return t
    except: pass
    return ""

token = read_token()
headers = {"Content-Type":"application/json", "Authorization":f"Bearer {token}"}

# Check 中国能建 and 弘业期货 in detail
test_stocks = [
    ("601868.SH", "中国能建"),
    ("001236.SZ", "弘业期货"),
]

for ts_code, name in test_stocks:
    print(f"\n{'='*60}")
    print(f"详细检查: {name} ({ts_code})")
    print(f"{'='*60}")
    
    query = f"{ts_code} {name} 年报"
    payload = {"query":query, "channel":"neodata", "sub_channel":"workbuddy", "data_type":"api"}
    
    resp = requests.post(_ND_ENDPOINT, headers=headers, json=payload, timeout=50)
    data = resp.json()
    recalls = data.get("data", {}).get("apiData", {}).get("apiRecall", [])
    full_text = "\n".join(r.get("content", "") for r in recalls)
    
    # Find latest annual block
    annual_header_pat = re.compile(r'统计截止日期为(\d{4})1231的年报')
    m = annual_header_pat.search(full_text)
    
    if m:
        year = m.group(1)
        start = m.start()
        next_section = re.search(r'统计截止日期为', full_text[start + 1:])
        end = start + 1 + next_section.start() if next_section else len(full_text)
        block = full_text[start:end]
        
        print(f"\n--- {year}年报 block (全文) ---")
        for line in block.split('\n'):
            line = line.strip()
            if line:
                print(f"  {line}")
        
        # Check what profit_yoy related lines exist
        print(f"\n--- 净利润同比相关行 ---")
        for line in block.split('\n'):
            line = line.strip()
            if any(kw in line for kw in ['同比', '增长', '利润']):
                print(f"  >> {line}")

# Also check: does the old code's _parse_yoy_from_line match differently?
print(f"\n{'='*60}")
print("测试 _parse_yoy_from_line 匹配逻辑")
print(f"{'='*60}")

test_lines = [
    "归母净利润同比增长 21.66%",
    "归母净利润同比增长21.66%",
    "归母净利润同比增长-30.44%",
    "净利润同比增长-86.61%",
    "营业收入同比增长 7.97%",
    "营业收入同比增长3.71%",
]

for line in test_lines:
    m = re.search(r'同比增长\s*([-+]?\d+\.?\d*)%', line)
    if m:
        print(f"  {line} => {m.group(1)}")
    else:
        print(f"  {line} => NO MATCH")
