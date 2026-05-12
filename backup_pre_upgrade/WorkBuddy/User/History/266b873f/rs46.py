#!/usr/bin/env python3
# -*- coding: utf-8 -*-
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

# Query 光线传媒 and get the FULL annual block
test_stocks = [
    ("300251.SZ", "光线传媒"),
    ("603379.SH", "三美股份"),  # This one has report_date in JSON
]

for ts_code, name in test_stocks:
    print(f"\n{'='*60}")
    print(f"Querying: {name} ({ts_code})")
    print(f"{'='*60}")
    
    query = f"{ts_code} {name} 年报"
    payload = {"query":query, "channel":"neodata", "sub_channel":"workbuddy", "data_type":"api"}
    
    resp = requests.post(_ND_ENDPOINT, headers=headers, json=payload, timeout=50)
    data = resp.json()
    recalls = data.get("data", {}).get("apiData", {}).get("apiRecall", [])
    full_text = "\n".join(r.get("content", "") for r in recalls)
    
    # Find ALL annual blocks
    annual_header_pat = re.compile(r'统计截止日期为(\d{4})1231的年报')
    for m in annual_header_pat.finditer(full_text):
        year = m.group(1)
        start = m.start()
        next_section = re.search(r'统计截止日期为', full_text[start + 1:])
        end = start + 1 + next_section.start() if next_section else len(text)
        block = full_text[start:end]
        
        print(f"\n--- {year}年报 block ---")
        # Print ALL lines
        for line in block.split('\n'):
            line = line.strip()
            if line:
                print(f"  {line}")
        
        # Check if 净利润 line exists (not 归母/扣非)
        found_净利润 = False
        for line in block.split('\n'):
            line = line.strip()
            if line.startswith('净利润') and '归母' not in line and '扣非' not in line:
                found_净利润 = True
                print(f"\n  [MATCH] {line}")
                break
        
        if not found_净利润:
            print(f"\n  [NO MATCH] No bare '净利润' line found in {year} annual block")
            # Check what profit lines exist
            for line in block.split('\n'):
                line = line.strip()
                if '净利润' in line or '利润' in line:
                    print(f"  [OTHER] {line}")
