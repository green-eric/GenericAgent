#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""统计有多少股票有直接OCF数据"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from qa_scorer import (
    Config, load_token, fetch_quarterly_data,
    _parse_single_block, _extract_all_report_sections,
    setup_logging
)

def check_ocf(ts_code, name):
    token = load_token()
    result = fetch_quarterly_data(ts_code, name, token)
    
    content = result.get("content", "")
    ttm_metrics = result.get("ttm_metrics", {})
    
    if not content:
        return None  # 缓存数据，无法判断
    
    sections = _extract_all_report_sections(content)
    quarterly_sections = [(d, t, txt) for d, t, txt in sections if "季报" in t]
    
    for i, (d, t, txt) in enumerate(quarterly_sections[:4]):
        parsed = _parse_single_block(txt)
        if parsed.get('ocf_abs') is not None:
            return True  # 有直接OCF
    return False  # 无直接OCF

if __name__ == "__main__":
    setup_logging()
    
    stock_file = os.path.join(Config.BASE_DIR, "xuan.txt")
    stocks = []
    with open(stock_file, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split()
            if len(parts) >= 2:
                stocks.append((parts[0], parts[1]))
    
    # 测试前50只
    has_ocf = 0
    no_ocf = 0
    cached = 0
    
    for i, (ts_code, name) in enumerate(stocks[:50]):
        try:
            result = check_ocf(ts_code, name)
            if result is None:
                cached += 1
            elif result:
                has_ocf += 1
            else:
                no_ocf += 1
        except Exception as e:
            print(f"  {ts_code} 异常: {e}")
        
        import time
        time.sleep(1)
    
    print(f"\n统计结果(前50只):")
    print(f"  有直接OCF: {has_ocf}")
    print(f"  无直接OCF: {no_ocf}")
    print(f"  缓存数据:  {cached}")
