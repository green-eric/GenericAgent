#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""查看电投水电完整原始文本"""

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
    print(f"共 {len(sections)} 个段落")
    
    for i, (d, t, txt) in enumerate(sections[:4]):
        print(f"\n{'='*60}")
        print(f"[{i+1}] {d} {t}")
        print(f"{'='*60}")
        # 打印完整文本（截断到2000字符）
        print(txt[:2000])
        if len(txt) > 2000:
            print(f"\n... (共{len(txt)}字符，已截断)")

if __name__ == "__main__":
    setup_logging()
    
    debug_raw("600292", "电投水电")
