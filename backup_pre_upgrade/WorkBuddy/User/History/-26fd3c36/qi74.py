#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sqlite3, os, sys
sys.path.insert(0, r'D:\Project\AnnualScorer')
from annual_scorer import *

Config.BASE_DIR = r'D:\Project\AnnualScorer'
Config.DB_FILE = os.path.join(Config.BASE_DIR, 'stock_cache.db')
conn = sqlite3.connect(Config.DB_FILE)

# 用户贴出的 Excel 数据
excel = {
    '600338.SH': {'总分': 75.6, '评级': 'A', '盈利': 74, '成长': 80, '现金流': 80, '偿债': 60},
    '300502.SZ': {'总分': 72.2, '评级': 'B', '盈利': 89.72, '成长': 92.89, '现金流': 14.07, '偿债': 56.3},
    '300308.SZ': {'总分': 69.1, '评级': 'B', '盈利': 79.87, '成长': 85.15, '现金流': 28.15, '偿债': 59.81},
    '600186.SH': {'总分': 66.2, '评级': 'B', '盈利': 75, '成长': 74, '现金流': 70, '偿债': 0},
    '300503.SZ': {'总分': 66.2, '评级': 'B', '盈利': 60, '成长': 94, '现金流': 60, '偿债': 20},
    '002463.SZ': {'总分': 62.91, '评级': 'B', '盈利': 77.06, '成长': 75.3, '现金流': 35.19, '偿债': 24.63},
    '002916.SZ': {'总分': 61.71, '评级': 'B', '盈利': 66.85, '成长': 66.15, '现金流': 59.81, '偿债': 31.67},
    '002033.SZ': {'总分': 60.45, '评级': 'B', '盈利': 80.22, '成长': 28.85, '现金流': 52.78, '偿债': 91.48},
}

test = [
    ('600338.SH', '西藏珠峰', '机械设备'),
    ('300502.SZ', '新易盛', '通信'),
    ('300308.SZ', '中际旭创', '通信'),
    ('600186.SH', '莲花控股', '机械设备'),
    ('300503.SZ', '昊志机电', '机械设备'),
    ('002463.SZ', '沪电股份', '电子'),
    ('002916.SZ', '深南电路', '电子'),
    ('002033.SZ', '丽江股份', '服务社会'),
]

all_stocks = []
for ts_code, name, industry in test:
    cur = conn.execute(
        'SELECT report_date, roe, gross_margin, net_margin, revenue_yoy, profit_yoy, debt_ratio, net_profit, ocf_abs '
        'FROM financial_reports WHERE ts_code=? AND report_type="annual" AND fetch_success=1 '
        'ORDER BY report_date DESC LIMIT 1', (ts_code,))
    row = cur.fetchone()
    if row:
        all_stocks.append({
            'ts_code': ts_code, 'name': name, 'industry_l1': industry,
            'report_date': row[0], 'roe': row[1], 'gross_margin': row[2],
            'net_margin': row[3], 'revenue_yoy': row[4], 'profit_yoy': row[5],
            'debt_ratio': row[6], 'net_profit': row[7], 'ocf_abs': row[8],
            'fetch_success': True
        })

industry_groups = {}
for s in all_stocks:
    ind = s.get('industry_l1', '未知')
    industry_groups.setdefault(ind, []).append(s)

print(f'{"代码":<12} {"名称":<8} {"总分":>6} {"评级":>4} {"盈利":>6} {"成长":>6} {"现金流":>6} {"偿债":>6}  |  {"Excel总分":>8} {"Excel评级":>8} {"总分差":>6}')
print('-'*100)

all_ok = True
for s in all_stocks:
    score = calc_score(s, industry_groups, all_stocks)
    ex = excel.get(s['ts_code'], {})
    diff = round(score['total_score'] - ex.get('总分', 0), 2)
    match = 'OK' if abs(diff) < 0.5 else 'DIFF'
    if match == 'DIFF':
        all_ok = False
    print(f'{score["ts_code"]:<12} {score["name"]:<8} {score["total_score"]:>6} {score["grade"]:>4} {score["profit_score"]:>6} {score["growth_score"]:>6} {score["ocf_score"]:>6} {score["debt_score"]:>6}  |  {ex.get("总分", "-"):>8} {ex.get("评级", "-"):>8} {diff:>6} {match}')

conn.close()
print('-'*100)
if all_ok:
    print('>>> 所有数据一致，评分计算正确！')
else:
    print('>>> 存在差异，需要检查')
