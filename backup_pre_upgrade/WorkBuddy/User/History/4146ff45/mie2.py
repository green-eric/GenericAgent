#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json, io, sys

# Force UTF-8 output
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

JSON_FILE = r'c:\Users\green\WorkBuddy\20260424203734\workplace\股票分析数据_20260426_000332.json'

excel_data = {
    '300139.SZ': {
        'name': '晓程科技',
        'industry_l1': '有色金属',
        'annual_report_date': '20251231',
        'annual_roe': 14.02,
        'annual_gross_margin': 62.48,
        'annual_net_margin': 29.2,
        'annual_revenue_yoy': 80.08,
        'annual_profit_yoy': 225.26,
        'annual_ocf_to_profit': 1.564755852,
        'annual_debt_ratio': 21.06,
        'score_profit': 92.7,
        'score_growth': 92.9,
        'score_ocf': 70.5,
        'score_debt': 85.6,
        'total_score': 88.01,
    },
    '002755.SZ': {
        'name': '奥赛康',
        'industry_l1': '建筑装饰',
        'annual_report_date': '20241231',
        'annual_roe': 5.38,
        'annual_gross_margin': 81.34,
        'annual_net_margin': 7.23,
        'annual_revenue_yoy': 23.15,
        'annual_profit_yoy': 207.92,
        'annual_ocf_to_profit': 3.201981293,
        'annual_debt_ratio': 22.37,
        'score_profit': 83.5,
        'score_growth': 90.8,
        'score_ocf': 84.7,
        'score_debt': 91.3,
        'total_score': 87.42,
    }
}

with open(JSON_FILE, 'r', encoding='utf-8') as f:
    d = json.load(f)

stocks = {s['ts_code']: s for s in d['stocks']}

print("=" * 90)
print("全字段对比测试：Excel 报告 vs JSON 数据")
print("=" * 90)

all_pass = True

for ts_code, expected in excel_data.items():
    print(f"\n{'-' * 90}")
    print(f"[{expected['name']} {ts_code}]")
    print(f"{'-' * 90}")
    
    actual = stocks.get(ts_code)
    if not actual:
        print(f"  [FAIL] JSON 中未找到该股票")
        all_pass = False
        continue
    
    field_map = [
        ('股票名称',     'name',                  None,    None),
        ('一级行业',     'industry_l1',           None,    None),
        ('年报日期',     'annual_report_date',    None,    None),
        ('加权ROE(%)',   'annual_roe',            2,       None),
        ('毛利率(%)',    'annual_gross_margin',   2,       None),
        ('净利率(%)',    'annual_net_margin',     2,       None),
        ('营收同比(%)',  'annual_revenue_yoy',    2,       None),
        ('净利润同比(%)','annual_profit_yoy',     2,       None),
        ('经营现金流/净利润','annual_ocf_to_profit', 9,   None),
        ('资产负债率(%)','annual_debt_ratio',     2,       None),
        ('盈利评分',     'detail',                None,    'score_profit'),
        ('成长评分',     'detail',                None,    'score_growth'),
        ('现金流评分',   'detail',                None,    'score_ocf'),
        ('偿债评分',     'detail',                None,    'score_debt'),
        ('总评分',       'total_score',           2,       None),
    ]
    
    for label, key, decimals, subkey in field_map:
        raw = actual.get(key)
        if subkey and isinstance(raw, dict):
            raw = raw.get(subkey)
        
        if decimals is not None and raw is not None:
            val = round(raw, decimals)
        else:
            val = raw
        
        exp = expected.get(subkey if subkey else key)
        
        if isinstance(exp, float) and isinstance(val, float):
            tol = 10 ** (-decimals) * 2 if decimals else 0.02
            match = abs(val - exp) < tol
        else:
            match = (val == exp) or (val is None and exp is None)
        
        status = "[PASS]" if match else "[FAIL]"
        if not match:
            all_pass = False
            print(f"  {status} {label:<12s} | Excel: {str(exp):>15} | JSON: {str(val):>15}  <-- 不一致")
        else:
            print(f"  {status} {label:<12s} | {val}")
    
    print(f"\n  --- JSON 额外字段（Excel 不包含）---")
    extra_fields = [
        ('评级',           'rating'),
        ('净利润(元)',     'annual_net_profit'),
        ('扣非净利润(元)', 'annual_deducted_profit'),
        ('营业收入(元)',   'annual_revenue'),
        ('经营现金流(元)', 'annual_ocf_abs'),
        ('总资产周转率',   'total_asset_turnover'),
        ('应收账款周转率', 'ar_turnover'),
        ('数据完整度',     'completeness'),
        ('置信度',         'confidence'),
        ('fetch_success',  'fetch_success'),
    ]
    for label, key in extra_fields:
        val = actual.get(key)
        if isinstance(val, float):
            val = round(val, 4)
        print(f"  [INFO] {label:<14s} | {val}")

print(f"\n{'=' * 90}")
if all_pass:
    print("结论: [PASS] 全部 15 个 Excel 字段与 JSON 一致")
else:
    print("结论: [FAIL] 存在不一致字段")
print(f"{'=' * 90}")
