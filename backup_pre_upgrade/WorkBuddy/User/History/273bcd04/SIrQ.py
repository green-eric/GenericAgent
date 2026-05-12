#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""验证评分结果"""
import sqlite3, os, sys
sys.path.insert(0, r'D:\Project\AnnualScorer')
from annual_scorer import *

Config.BASE_DIR = r'D:\Project\AnnualScorer'
Config.DB_FILE = os.path.join(Config.BASE_DIR, 'stock_cache.db')

conn = sqlite3.connect(Config.DB_FILE)

test_stocks = [
    ('600338.SH', '西藏珠峰', '机械设备'),
    ('300502.SZ', '新易盛', '通信'),
    ('300308.SZ', '中际旭创', '通信'),
    ('600186.SH', '莲花控股', '机械设备'),
    ('300503.SZ', '昊志机电', '机械设备'),
    ('002463.SZ', '沪电股份', '电子'),
    ('002916.SZ', '深南电路', '电子'),
    ('002033.SZ', '丽江股份', '社会服务'),
]

print('='*100)
header = f'{"代码":<12} {"名称":<8} {"行业":<8} {"总分":>6} {"评级":>4} {"盈利":>6} {"成长":>6} {"现金流":>6} {"偿债":>6} {"ROE":>6} {"净利率":>6} {"营收同比":>8} {"净利同比":>8} {"负债率":>6} {"OCF比":>8}'
print(header)
print('-'*100)

all_stocks = []
for ts_code, name, industry in test_stocks:
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
    else:
        print(f'  [警告] {ts_code} {name} 数据库中无数据')

industry_groups = {}
for s in all_stocks:
    ind = s.get('industry_l1', '未知')
    if ind not in industry_groups:
        industry_groups[ind] = []
    industry_groups[ind].append(s)

for s in all_stocks:
    score = calc_score(s, industry_groups, all_stocks)
    ocf_ratio = ''
    if s.get('net_profit') and s.get('ocf_abs') and s['net_profit'] != 0:
        ocf_ratio = str(round(s['ocf_abs'] / s['net_profit'] * 100, 2))
    
    row_str = (
        f'{score["ts_code"]:<12} {score["name"]:<8} {score["industry_l1"]:<8} '
        f'{score["total_score"]:>6} {score["grade"]:>4} '
        f'{score["profit_score"]:>6} {score["growth_score"]:>6} '
        f'{score["ocf_score"]:>6} {score["debt_score"]:>6} '
        f'{str(score["roe"]) if score["roe"] is not None else "N/A":>6} '
        f'{str(score["net_margin"]) if score["net_margin"] is not None else "N/A":>6} '
        f'{str(score["revenue_yoy"]) if score["revenue_yoy"] is not None else "N/A":>8} '
        f'{str(score["profit_yoy"]) if score["profit_yoy"] is not None else "N/A":>8} '
        f'{str(score["debt_ratio"]) if score["debt_ratio"] is not None else "N/A":>6} '
        f'{ocf_ratio:>8}'
    )
    print(row_str)

conn.close()
print('='*100)
