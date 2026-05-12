#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""测试数据验证：从 NeoData 拉取股票数据并与评分结果对比"""
import sys, os, json
sys.path.insert(0, r'D:\Project\AnnualScorer')
from annual_scorer import *

Config.BASE_DIR = r'D:\Project\AnnualScorer'

# 测试股票列表（用户提供的8只）
test_stocks = [
    {'ts_code': '600338.SH', 'name': '西藏珠峰'},
    {'ts_code': '300502.SZ', 'name': '新易盛'},
    {'ts_code': '300308.SZ', 'name': '中际旭创'},
    {'ts_code': '600186.SH', 'name': '莲花控股'},
    {'ts_code': '300503.SZ', 'name': '昊志机电'},
    {'ts_code': '002463.SZ', 'name': '沪电股份'},
    {'ts_code': '002916.SZ', 'name': '深南电路'},
    {'ts_code': '002033.SZ', 'name': '丽江股份'},
]

# 用户提供的 Excel 数据（用于对比）
excel_data = {
    '600338.SH': {'总分': 75.6, '评级': 'A', '盈利': 74, '成长': 80, '现金流': 80, '偿债': 60, 'ROE': 6.7, '净利率': 13.18, '营收同比': 11.64, '净利同比': 206.62, '负债率': 40.31, 'OCF比': 341.76},
    '300502.SZ': {'总分': 72.2, '评级': 'B', '盈利': 89.72, '成长': 92.89, '现金流': 14.07, '偿债': 56.3, 'ROE': 41, '净利率': 32.82, '营收同比': 179.15, '净利同比': 312.26, '负债率': 32.11, 'OCF比': 22.59},
    '300308.SZ': {'总分': 69.1, '评级': 'B', '盈利': 79.87, '成长': 85.15, '现金流': 28.15, '偿债': 59.81, 'ROE': 31.23, '净利率': 22.51, '营收同比': 122.64, '净利同比': 137.93, '负债率': 29.7, 'OCF比': 58.91},
    '600186.SH': {'总分': 66.2, '评级': 'B', '盈利': 75, '成长': 74, '现金流': 70, '偿债': 0, 'ROE': 12.35, '净利率': 7.54, '营收同比': 25.98, '净利同比': 55.92, '负债率': 58.35, 'OCF比': 326.87},
    '300503.SZ': {'总分': 66.2, '评级': 'B', '盈利': 60, '成长': 94, '现金流': 60, '偿债': 20, 'ROE': 7.27, '净利率': 6.37, '营收同比': 30.63, '净利同比': 142.74, '负债率': 54.71, 'OCF比': 162.25},
    '002463.SZ': {'总分': 62.91, '评级': 'B', '盈利': 77.06, '成长': 75.3, '现金流': 35.19, '偿债': 24.63, 'ROE': 24.25, '净利率': 19.24, '营收同比': 49.26, '净利同比': 71.05, '负债率': 43.81, 'OCF比': 90.6},
    '002916.SZ': {'总分': 61.71, '评级': 'B', '盈利': 66.85, '成长': 66.15, '现金流': 59.81, '偿债': 31.67, 'ROE': 13.58, '净利率': 10.49, '营收同比': 32.39, '净利同比': 34.29, '负债率': 42.12, 'OCF比': 158.74},
    '002033.SZ': {'总分': 60.45, '评级': 'B', '盈利': 80.22, '成长': 28.85, '现金流': 52.78, '偿债': 91.48, 'ROE': 8.44, '净利率': 29.25, '营收同比': 1.19, '净利同比': -7.27, '负债率': 11.68, 'OCF比': 139.17},
}

print("=" * 80)
print("数据验证：从 NeoData 重新获取年报数据")
print("=" * 80)

token = load_token()
results = []

for stock in test_stocks:
    ts_code = stock['ts_code']
    name = stock['name']
    print(f"\n--- {ts_code} {name} ---")
    
    # 获取年报数据
    data = fetch_stock_finance(ts_code, name, token)
    
    if data['fetch_success']:
        metrics = data['metrics']
        print(f"  年报日期: {data.get('report_date', 'N/A')}")
        print(f"  ROE: {metrics.get('roe', 'N/A')}%")
        print(f"  毛利率: {metrics.get('gross_margin', 'N/A')}%")
        print(f"  净利率: {metrics.get('net_margin', 'N/A')}%")
        print(f"  营收同比: {metrics.get('revenue_yoy', 'N/A')}%")
        print(f"  净利同比: {metrics.get('profit_yoy', 'N/A')}%")
        print(f"  负债率: {metrics.get('debt_ratio', 'N/A')}%")
        print(f"  净利润: {metrics.get('net_profit', 'N/A')}")
        print(f"  经营现金流: {metrics.get('ocf_abs', 'N/A')}")
        
        # 对比 Excel 数据
        excel = excel_data.get(ts_code, {})
        print(f"  [对比Excel] Excel中ROE={excel.get('ROE', 'N/A')}%, 获取到ROE={metrics.get('roe', 'N/A')}%")
        
        results.append({'ts_code': ts_code, 'name': name, 'metrics': metrics, 'data': data})
    else:
        print(f"  [失败] 未获取到有效年报数据")
        print(f"  has_valid_block: {data.get('has_valid_block', False)}")

print("\n" + "=" * 80)
print("验证总结")
print("=" * 80)
print(f"成功获取: {len(results)}/{len(test_stocks)} 只股票")
