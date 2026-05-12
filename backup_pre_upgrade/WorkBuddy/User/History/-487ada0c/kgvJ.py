#!/usr/bin/env python3
"""Verify 300308.SZ 中际旭创 2025年报 data"""
import json
import re
import subprocess
import sys

cmd = [
    sys.executable,
    r'C:\Users\green\.workbuddy\plugins\marketplaces\cb_teams_marketplace\plugins\finance-data\skills\neodata-financial-search\scripts\query.py',
    '--query', '300308.SZ 中际旭创 2025年报 财务指标 ROE 毛利率 净利率 营收同比 净利润同比 经营现金流 资产负债率',
    '--data-type', 'api'
]

result = subprocess.run(cmd, capture_output=True)
raw = result.stdout.decode('utf-8')

# Strip CLIXML
raw = re.sub(r'#< CLIXML.*', '', raw, flags=re.DOTALL)
raw = re.sub(r'<Objs.*', '', raw, flags=re.DOTALL)

m = re.search(r'\{.*\}', raw, re.DOTALL)
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
    print(raw[:1000])
