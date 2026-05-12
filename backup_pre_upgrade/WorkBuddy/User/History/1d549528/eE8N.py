#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""查看电投水电原始文本中所有含'经营'或'现金流'或'现金'的行"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from qa_scorer import (
    Config, load_token, fetch_quarterly_data,
    _extract_all_report_sections, setup_logging
)

def debug_raw(ts_code, name):
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
    sections = _extract_all_report_sections(content)
    
    print(f"\n{'='*60}")
    print(f"股票: {ts_code} {name}")
    
    for i, (d, t, txt) in enumerate(sections[:6]):
        print(f"\n--- [{i+1}] {d} {t} ---")
        for line in txt.split("\n"):
            line_s = line.strip()
            if any(kw in line_s for kw in ["经营", "现金流", "现金", "净利润"]):
                print(f"  {line_s}")

if __name__ == "__main__":
    setup_logging()
    
    test_stocks = [
        ("600292", "电投水电"),
        ("601901", "方正证券"),
        ("000997", "新大陆"),
    ]
    
    for ts_code, name in test_stocks:
        try:
            debug_raw(ts_code, name)
        except Exception as e:
            print(f"\n{ts_code} {name} 异常: {e}")
        
        import time
        time.sleep(2)
