#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""调试ROE为None的问题"""

import os
import sys
import re

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from qa_scorer import (
    Config, load_token, fetch_quarterly_data,
    _parse_single_block, _extract_all_report_sections,
    setup_logging
)

def debug_stock(ts_code, name):
    # 清除缓存
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
    latest = result.get("latest_quarterly", {})
    
    sections = _extract_all_report_sections(content)
    quarterly_sections = [(d, t, txt) for d, t, txt in sections if "季报" in t]
    
    print(f"\n{'='*60}")
    print(f"股票: {ts_code} {name}")
    print(f"{'='*60}")
    
    # 检查最新单季报的净资产相关字段
    if quarterly_sections:
        latest_q = quarterly_sections[0]
        print(f"\n最新季报: {latest_q[0]} {latest_q[1]}")
        parsed = _parse_single_block(latest_q[2])
        
        print(f"\n净资产相关字段:")
        print(f"  net_assets = {parsed.get('net_assets')}")
        print(f"  total_assets = {parsed.get('total_assets')}")
        print(f"  total_liabilities = {parsed.get('total_liabilities')}")
        
        # 检查原始文本中是否有净资产相关行
        print(f"\n原始文本中净资产相关行:")
        for line in latest_q[2].split("\n"):
            line_s = line.strip()
            if any(kw in line_s for kw in ["净资产", "股东权益", "所有者权益", "资产合计", "负债合计", "资产总", "负债总"]):
                print(f"  {line_s}")
    
    print(f"\nTTM ROE = {ttm_metrics.get('roe_ttm')}")
    print(f"TTM 净利润 = {ttm_metrics.get('net_profit_ttm')}")
    
    # 检查所有季报段落的净资产
    print(f"\n各季度净资产数据:")
    for i, (d, t, txt) in enumerate(quarterly_sections[:4]):
        parsed = _parse_single_block(txt)
        print(f"  {d} {t}: net_assets={parsed.get('net_assets')}, total_assets={parsed.get('total_assets')}, total_liab={parsed.get('total_liabilities')}")
    
    # 检查最新单季报原始文本中是否有资产/负债数据
    if quarterly_sections:
        print(f"\n最新季报完整文本中的财务数据行:")
        for line in quarterly_sections[0][2].split("\n"):
            line_s = line.strip()
            if any(kw in line_s for kw in ["资产", "负债", "权益", "ROE", "净资产"]):
                print(f"  {line_s}")

if __name__ == "__main__":
    setup_logging()
    
    # 测试几只ROE为None的股票
    test_stocks = [
        ("601901", "方正证券"),
        ("600292", "电投水电"),
        ("000997", "新大陆"),
    ]
    
    for ts_code, name in test_stocks:
        try:
            debug_stock(ts_code, name)
        except Exception as e:
            print(f"\n{ts_code} {name} 调试异常: {e}")
        
        import time
        time.sleep(2)
