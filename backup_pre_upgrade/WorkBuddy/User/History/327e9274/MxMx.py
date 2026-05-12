#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""调试经营现金流提取"""

import os
import sys
import re

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from qa_scorer import (
    Config, load_token, fetch_quarterly_data,
    _parse_single_block, _extract_all_report_sections,
    setup_logging
)

def debug_ocf(ts_code, name):
    import sqlite3
    db_path = Config.QUARTERLY_DB_FILE
    try:
        conn = sqlite3.connect(db_path)
        conn.execute("DELETE FROM quarterly_cache WHERE ts_code = ?", (ts_code,))
        conn.commit()
        conn.close()
    except:
        pass
    
    token = load_token()
    result = fetch_quarterly_data(ts_code, name, token)
    
    content = result.get("content", "")
    ttm_metrics = result.get("ttm_metrics", {})
    
    sections = _extract_all_report_sections(content)
    quarterly_sections = [(d, t, txt) for d, t, txt in sections if "季报" in t]
    
    print(f"\n{'='*60}")
    print(f"股票: {ts_code} {name}")
    print(f"OCF(TTM) = {ttm_metrics.get('ocf_abs_ttm')}")
    print(f"OCF/净利润(TTM) = {ttm_metrics.get('ocf_ratio_ttm')}")
    print(f"净利润(TTM) = {ttm_metrics.get('net_profit_ttm')}")
    
    print(f"\n各季度经营现金流相关行:")
    for i, (d, t, txt) in enumerate(quarterly_sections[:6]):
        print(f"\n  [{i+1}] {d} {t}")
        parsed = _parse_single_block(txt)
        print(f"      ocf_abs = {parsed.get('ocf_abs')}")
        print(f"      ocf_ratio = {parsed.get('ocf_ratio')}")
        print(f"      net_profit = {parsed.get('net_profit')}")
        
        # 显示原始文本中所有含"现金流"的行
        for line in txt.split("\n"):
            line_s = line.strip()
            if "现金流" in line_s or "现金流量" in line_s:
                print(f"      原始行: {line_s}")

if __name__ == "__main__":
    setup_logging()
    
    # 测试OCF异常的股票
    test_stocks = [
        ("600292", "电投水电"),
        ("000701", "厦门信达"),
        ("300516", "久之洋"),
    ]
    
    for ts_code, name in test_stocks:
        try:
            debug_ocf(ts_code, name)
        except Exception as e:
            print(f"\n{ts_code} {name} 调试异常: {e}")
        
        import time
        time.sleep(2)
