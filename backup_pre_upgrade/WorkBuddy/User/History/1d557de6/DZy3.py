#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""查看600292完整API返回"""

import os
import sys
import json

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from qa_scorer import (
    Config, load_token, fetch_quarterly_data,
    _extract_all_report_sections, setup_logging
)

token = load_token()
result = fetch_quarterly_data("600292", "电投水电", token)

print(f"fetch_success: {result.get('fetch_success')}")
print(f"quarter_count: {result.get('quarter_count')}")
print(f"latest_quarter: {result.get('latest_quarter')}")
print(f"content length: {len(result.get('content', ''))}")
print(f"ttm_metrics: {json.dumps(result.get('ttm_metrics', {}), ensure_ascii=False, indent=2)}")
print(f"latest_quarterly: {json.dumps(result.get('latest_quarterly', {}), ensure_ascii=False, indent=2)}")

content = result.get("content", "")
if content:
    sections = _extract_all_report_sections(content)
    print(f"\n段落数: {len(sections)}")
    for i, (d, t, txt) in enumerate(sections[:2]):
        print(f"\n[{i+1}] {d} {t} ({len(txt)}字符)")
        print(txt[:1000])
else:
    print("\ncontent为空!")
