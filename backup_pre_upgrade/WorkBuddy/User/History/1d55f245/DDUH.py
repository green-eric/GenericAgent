#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""检查OCF是直接取还是兜底计算的"""

import os
import sys
import re

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from qa_scorer import (
    Config, load_token, fetch_quarterly_data,
    _parse_single_block, _extract_all_report_sections,
    _compute_ttm, setup_logging
)

def check_ocf_source(ts_code, name):
    # 先不清缓存，直接用已有数据
    token = load_token()
    result = fetch_quarterly_data(ts_code, name, token)
    
    content = result.get("content", "")
    ttm_metrics = result.get("ttm_metrics", {})
    
    # 如果content为空（从缓存读取），跳过详细分析
    if not content:
        print(f"\n{ts_code} {name}: content为空(缓存数据), OCF={ttm_metrics.get('ocf_abs_ttm')}, OCF/净利润={ttm_metrics.get('ocf_ratio_ttm')}")
        return
    
    sections = _extract_all_report_sections(content)
    quarterly_sections = [(d, t, txt) for d, t, txt in sections if "季报" in t]
    
    print(f"\n{ts_code} {name}:")
    print(f"  OCF(TTM)={ttm_metrics.get('ocf_abs_ttm')}, OCF/净利润={ttm_metrics.get('ocf_ratio_ttm')}")
    
    has_direct_ocf = False
    for i, (d, t, txt) in enumerate(quarterly_sections[:4]):
        parsed = _parse_single_block(txt)
        ocf_abs = parsed.get('ocf_abs')
        ocf_ratio = parsed.get('ocf_ratio')
        np_val = parsed.get('net_profit')
        
        if ocf_abs is not None:
            has_direct_ocf = True
            print(f"  {d}: ✅ 直接OCF={ocf_abs/1e8:.2f}亿, 净利润现金含量={ocf_ratio}%, 净利润={np_val/1e8:.2f}亿")
        else:
            print(f"  {d}: ❌ 无直接OCF, 净利润现金含量={ocf_ratio}%, 净利润={np_val/1e8:.2f}亿 (将用兜底)")
    
    if not has_direct_ocf:
        print(f"  ⚠️ 所有季度均无直接OCF数据，完全依赖净利润现金含量兜底")

if __name__ == "__main__":
    setup_logging()
    
    # OCF异常的股票
    test_stocks = [
        ("600292", "电投水电"),
        ("000701", "厦门信达"),
        ("300516", "久之洋"),
        ("000825", "太钢不锈"),
        ("600310", "广西能源"),
        ("000007", "全新好"),
        ("300494", "盛天网络"),
    ]
    
    for ts_code, name in test_stocks:
        try:
            check_ocf_source(ts_code, name)
        except Exception as e:
            print(f"\n{ts_code} {name} 异常: {e}")
        
        import time
        time.sleep(1)
