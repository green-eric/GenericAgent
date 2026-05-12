#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""验证评分结果与Excel数据是否一致"""
import sqlite3, os, sys
sys.path.insert(0, r'D:\Project\AnnualScorer')
from annual_scorer import calc_score, calc_completeness, percentile_rank

# 用户贴出的8只股票的Excel数据
excel_data = {
    '600338.SH': {
        'name': '西藏珠峰', 'industry': '机械设备',
        '总分': 75.6, '评级': 'A',
        '盈利': 74, '成长': 80, '现金流': 80, '偿债': 60,
        'ROE': 6.7, '毛利率': 46.73, '净利率': 13.18,
        '营收同比': 11.64, '净利同比': 206.62, '负债率': 40.31,
        'OCF比': 341.76, '净利润': 216138822.6, '经营现金流': 738673787.5,
    },
    '300502.SZ': {
        'name': '新易盛', 'industry': '通信',
        '总分': 72.2, '评级': 'B',
        '盈利': 89.72, '成长': 92.89, '现金流': 14.07, '偿债': 56.3,
        'ROE': 41, '毛利率': 44.72, '净利率': 32.82,
        '营收同比': 179.15, '净利同比': 312.26, '负债率': 32.11,
        'OCF比': 22.59, '净利润': 2837813624, '经营现金流': 640930145.6,
    },
    '300308.SZ': {
        'name': '中际旭创', 'industry': '通信',
        '总分': 69.1, '评级': 'B',
        '盈利': 79.87, '成长': 85.15, '现金流': 28.15, '偿债': 59.81,
        'ROE': 31.23, '毛利率': 33.8, '净利率': 22.51,
        '营收同比': 122.64, '净利同比': 137.93, '负债率': 29.7,
        'OCF比': 58.91, '净利润': 5371775139, '经营现金流': 3164582958,
    },
    '600186.SH': {
        'name': '莲花控股', 'industry': '机械设备',
        '总分': 66.2, '评级': 'B',
        '盈利': 75, '成长': 74, '现金流': 70, '偿债': 0,
        'ROE': 12.35, '毛利率': 25.3, '净利率': 7.54,
        '营收同比': 25.98, '净利同比': 55.92, '负债率': 58.35,
        'OCF比': 326.87, '净利润': 199547068.1, '经营现金流': 652264004.2,
    },
    '300503.SZ': {
        'name': '昊志机电', 'industry': '机械设备',
        '总分': 66.2, '评级': 'B',
        '盈利': 60, '成长': 94, '现金流': 60, '偿债': 20,
        'ROE': 7.27, '毛利率': 34.5, '净利率': 6.37,
        '营收同比': 30.63, '净利同比': 142.74, '负债率': 54.71,
        'OCF比': 162.25, '净利润': 83185085.99, '经营现金流': 134964770.4,
    },
    '002463.SZ': {
        'name': '沪电股份', 'industry': '电子',
        '总分': 62.91, '评级': 'B',
        '盈利': 77.06, '成长': 75.3, '现金流': 35.19, '偿债': 24.63,
        'ROE': 24.25, '毛利率': 34.54, '净利率': 19.24,
        '营收同比': 49.26, '净利同比': 71.05, '负债率': 43.81,
        'OCF比': 90.6, '净利润': 2566315235, '经营现金流': 2325184965,
    },
    '002916.SZ': {
        'name': '深南电路', 'industry': '电子',
        '总分': 61.71, '评级': 'B',
        '盈利': 66.85, '成长': 66.15, '现金流': 59.81, '偿债': 31.67,
        'ROE': 13.58, '毛利率': 24.83, '净利率': 10.49,
        '营收同比': 32.39, '净利同比': 34.29, '负债率': 42.12,
        'OCF比': 158.74, '净利润': 1878722169, '经营现金流': 2982221520,
    },
    '002033.SZ': {
        'name': '丽江股份', 'industry': '社会服务',
        '总分': 60.45, '评级': 'B',
        '盈利': 80.22, '成长': 28.85, '现金流': 52.78, '偿债': 91.48,
        'ROE': 8.44, '毛利率': 57.37, '净利率': 29.25,
        '营收同比': 1.19, '净利同比': -7.27, '负债率': 11.68,
        'OCF比': 139.17, '净利润': 236486695.7, '经营现金流': 329125983.7,
    },
}

print("=" * 110)
print("评分验证：重新计算 vs Excel 数据对比")
print("=" * 110)

# 构建股票列表
all_stocks = []
for ts_code, d in excel_data.items():
    all_stocks.append({
        'ts_code': ts_code,
        'name': d['name'],
        'industry_l1': d['industry'],
        'roe': d['ROE'],
        'gross_margin': d['毛利率'],
        'net_margin': d['净利率'],
        'revenue_yoy': d['营收同比'],
        'profit_yoy': d['净利同比'],
        'debt_ratio': d['负债率'],
        'net_profit': d['净利润'],
        'ocf_abs': d['经营现金流'],
        'fetch_success': True,
    })

# 行业分组
industry_groups = {}
for s in all_stocks:
    ind = s['industry_l1']
    industry_groups.setdefault(ind, []).append(s)

# 表头
hdr = f'{"代码":<12} {"名称":<8} {"计算总分":>8} {"Excel总分":>10} {"总分差":>7} {"计算评级":>8} {"Excel评级":>8} {"盈利差":>7} {"成长差":>7} {"现金流差":>8} {"偿债差":>7}'
print(hdr)
print('-' * 110)

all_ok = True
for s in all_stocks:
    score = calc_score(s, industry_groups, all_stocks)
    ex = excel_data[s['ts_code']]
    
    diff_total = round(score['total_score'] - ex['总分'], 2)
    diff_profit = round(score['profit_score'] - ex['盈利'], 2)
    diff_growth = round(score['growth_score'] - ex['成长'], 2)
    diff_ocf = round(score['ocf_score'] - ex['现金流'], 2)
    diff_debt = round(score['debt_score'] - ex['偿债'], 2)
    
    ok = abs(diff_total) < 0.5
    if not ok:
        all_ok = False
    
    mark = 'OK' if ok else '!!'
    print(f'{score["ts_code"]:<12} {score["name"]:<8} {score["total_score"]:>8} {ex["总分"]:>10} {diff_total:>7} {score["grade"]:>8} {ex["评级"]:>8} {diff_profit:>7} {diff_growth:>7} {diff_ocf:>8} {diff_debt:>7}  {mark}')

print('-' * 110)
if all_ok:
    print('>>> 所有数据一致，评分计算正确！')
else:
    print('>>> 存在差异，需要检查')
print()

# 额外验证：检查完整度和OCF计算
print("辅助验证：")
for s in all_stocks:
    ex = excel_data[s['ts_code']]
    metrics = {
        'roe': s['roe'], 'gross_margin': s['gross_margin'],
        'net_margin': s['net_margin'], 'revenue_yoy': s['revenue_yoy'],
        'profit_yoy': s['profit_yoy'], 'debt_ratio': s['debt_ratio'],
        'net_profit': s['net_profit'], 'ocf_abs': s['ocf_abs'],
    }
    comp, level = calc_completeness(metrics)
    ocf_ratio = round(s['ocf_abs'] / s['net_profit'] * 100, 2) if s['net_profit'] and s['ocf_abs'] and s['net_profit'] != 0 else None
    
    ocf_match = 'OK' if ocf_ratio is None or abs(ocf_ratio - ex['OCF比']) < 1 else f'!! 计算={ocf_ratio} Excel={ex["OCF比"]}'
    print(f'  {s["ts_code"]} {s["name"]}: 完整度={comp:.0%}({level}), OCF比={ocf_ratio}%  {ocf_match}')
