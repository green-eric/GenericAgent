#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
对 300139.SZ(晓程科技) 和 002755.SZ(奥赛康) 做全字段测试
"""
import json, sys
sys.path.insert(0, r'c:\Users\green\WorkBuddy\20260424203734\workplace')
from stock_analyzer import StockAnalyzer

JSON_FILE = r'c:\Users\green\WorkBuddy\20260424203734\workplace\股票分析数据_20260426_000332.json'

# 用户提供的 Excel 数据
excel_data = {
    '300139.SZ': {
        'name': '晓程科技',
        'industry': '有色金属',
        'report_date': '2025-12-31',
        'roe': 14.02,
        'gross_margin': 62.48,
        'net_margin': 29.2,
        'revenue_yoy': 80.08,
        'profit_yoy': 225.26,
        'ocf_ratio': 1.564755852,
        'debt_ratio': 21.06,
        'score_profit': 92.7,
        'score_growth': 92.9,
        'score_ocf': 70.5,
        'score_debt': 85.6,
        'total_score': 88.01,
    },
    '002755.SZ': {
        'name': '奥赛康',
        'industry': '建筑装饰',
        'report_date': '2024-12-31',
        'roe': 5.38,
        'gross_margin': 81.34,
        'net_margin': 7.23,
        'revenue_yoy': 23.15,
        'profit_yoy': 207.92,
        'ocf_ratio': 3.201981293,
        'debt_ratio': 22.37,
        'score_profit': 83.5,
        'score_growth': 90.8,
        'score_ocf': 84.7,
        'score_debt': 91.3,
        'total_score': 87.42,
    }
}

# 从 JSON 读取
with open(JSON_FILE, 'r', encoding='utf-8') as f:
    d = json.load(f)

stocks = {s['ts_code']: s for s in d['stocks']}

print("=" * 80)
print("全字段对比测试：Excel 报告 vs JSON 数据")
print("=" * 80)

all_pass = True

for ts_code, expected in excel_data.items():
    print(f"\n{'─' * 80}")
    print(f"【{expected['name']} {ts_code}】")
    print(f"{'─' * 80}")
    
    actual = stocks.get(ts_code)
    if not actual:
        print(f"  ❌ JSON 中未找到该股票")
        all_pass = False
        continue
    
    # 所有字段对比
    field_map = [
        ('股票名称',    'name',         None),
        ('一级行业',    'industry_l1',  None),
        ('年报日期',    'annual_report_date', lambda v: str(v) if v else None),
        ('加权ROE(%)',  'annual_roe',   lambda v: round(v, 2) if v is not None else None),
        ('毛利率(%)',   'annual_gross_margin', lambda v: round(v, 2) if v is not None else None),
        ('净利率(%)',   'annual_net_margin', lambda v: round(v, 2) if v is not None else None),
        ('营收同比(%)', 'annual_revenue_yoy', lambda v: round(v, 2) if v is not None else None),
        ('净利润同比(%)','annual_profit_yoy', lambda v: round(v, 2) if v is not None else None),
        ('经营现金流/净利润','annual_ocf_to_profit', lambda v: round(v, 9) if v is not None else None),
        ('资产负债率(%)','annual_debt_ratio', lambda v: round(v, 2) if v is not None else None),
        ('盈利评分',    'detail',       lambda v: round(v.get('score_profit'), 1) if v else None),
        ('成长评分',    'detail',       lambda v: round(v.get('score_growth'), 1) if v else None),
        ('现金流评分',  'detail',       lambda v: round(v.get('score_ocf'), 1) if v else None),
        ('偿债评分',    'detail',       lambda v: round(v.get('score_debt'), 1) if v else None),
        ('总评分',      'total_score',  lambda v: round(v, 2) if v is not None else None),
        ('评级',        'rating',       None),
        ('净利润(元)',  'annual_net_profit', lambda v: round(v, 2) if v is not None else None),
        ('扣非净利润',  'annual_deducted_profit', lambda v: round(v, 2) if v is not None else None),
        ('营业收入',    'annual_revenue', lambda v: round(v, 2) if v is not None else None),
        ('经营现金流',  'annual_ocf_abs', lambda v: round(v, 2) if v is not None else None),
        ('总资产周转率','total_asset_turnover', lambda v: round(v, 2) if v is not None else None),
        ('应收账款周转','ar_turnover',  lambda v: round(v, 2) if v is not None else None),
        ('数据完整度',  'completeness',  None),
        ('置信度',      'confidence',    None),
        ('fetch_success','fetch_success', None),
    ]
    
    for label, key, transform in field_map:
        raw = actual.get(key)
        val = transform(raw) if transform else raw
        exp = expected.get(key)
        
        # 只在 Excel 有的字段做对比
        if exp is not None:
            match = (val == exp) or (val is None and exp is None)
            status = "✅" if match else "❌"
            if not match:
                all_pass = False
                print(f"  {status} {label}: Excel={exp} | JSON={val} ← 不一致")
            else:
                print(f"  {status} {label}: {val}")
        else:
            # JSON 独有字段，只显示
            print(f"  ℹ️  {label}: {val}")

print(f"\n{'=' * 80}")
print(f"结论: {'✅ 全部字段一致' if all_pass else '❌ 存在不一致字段'}")
print(f"{'=' * 80}")
