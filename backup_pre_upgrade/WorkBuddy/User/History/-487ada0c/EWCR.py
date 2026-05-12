#!/usr/bin/env python3
"""Verify 300308.SZ 中际旭创 2025年报 data"""
import json
import re
import subprocess
import sys
import os

# Force UTF-8 output
os.environ['PYTHONIOENCODING'] = 'utf-8'

cmd = [
    sys.executable,
    '-X', 'utf8',
    r'C:\Users\green\.workbuddy\plugins\marketplaces\cb_teams_marketplace\plugins\finance-data\skills\neodata-financial-search\scripts\query.py',
    '--query', '300308.SZ 中际旭创 2025年报 财务指标 ROE 毛利率 净利率 营收同比 净利润同比 经营现金流 资产负债率',
    '--data-type', 'api'
]

result = subprocess.run(cmd, capture_output=True)
raw = result.stdout.decode('utf-8', errors='replace')

# Strip CLIXML wrapper that PowerShell adds
raw = re.sub(r'#< CLIXML\r?\n?', '', raw)
raw = re.sub(r'<Objs[\s\S]*?</Objs>', '', raw)

m = re.search(r'\{[\s\S]*\}', raw)
if m:
    data = json.loads(m.group())
    api_recall = data['data']['apiData']['apiRecall']
    for item in api_recall:
        print(f'=== {item["type"]} ===')
        content = item.get('content', '')
        if isinstance(content, str):
            print(content[:5000])
        else:
            print(json.dumps(content, indent=2, ensure_ascii=False)[:5000])
        print()
else:
    print('No JSON found')
    print(repr(raw[:2000]))
