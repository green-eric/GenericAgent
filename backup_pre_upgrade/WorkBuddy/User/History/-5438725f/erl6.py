#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""查看 NeoData 返回的原始数据格式"""
import subprocess, json, re, sys, os, io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

query_script = os.path.expanduser(
    '~/.workbuddy/plugins/marketplaces/cb_teams_marketplace/'
    'plugins/finance-data/skills/neodata-financial-search/scripts/query.py'
)

res = subprocess.run(
    [sys.executable, query_script, '--query',
     '300308.SZ 中际旭创 2025年报 财务指标 ROE 毛利率 净利率 营收同比 净利润同比 经营现金流 资产负债率',
     '--data-type', 'api'],
    capture_output=True, text=True, timeout=60
)

out = res.stdout.strip()
out = re.sub(r'#< CLIXML\r?\n?', '', out)
out = re.sub(r'<Objs[\s\S]*?</Objs>', '', out)
out = out.strip()

if out:
    data = json.loads(out)
    recalls = data.get('data', {}).get('apiData', {}).get('apiRecall', [])
    for i, r in enumerate(recalls):
        print(f'=== Recall {i}: type={r.get("type")}, desc={r.get("desc")} ===')
        content = r.get('content', '')
        print(content[:5000])
        print()
else:
    print('Empty output')
    print('STDERR:', res.stderr[:500])
