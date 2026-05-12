#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sqlite3, os, sys
sys.path.insert(0, r'D:\Project\AnnualScorer')
from annual_scorer import *

Config.BASE_DIR = r'D:\Project\AnnualScorer'
Config.DB_FILE = os.path.join(Config.BASE_DIR, 'stock_cache.db')
conn = sqlite3.connect(Config.DB_FILE)

# 查找宏和科技
cur = conn.execute('SELECT ts_code, name, industry_l1 FROM stocks WHERE name LIKE "%宏和科技%"')
rows = cur.fetchall()
if not rows:
    # 模糊搜索
    cur = conn.execute('SELECT ts_code, name, industry_l1 FROM stocks WHERE name LIKE "%宏和%"')
    rows = cur.fetchall()

print('=== 搜索结果 ===')
for r in rows:
    print(r)

if rows:
    ts_code = rows[0][0]
    name = rows[0][1]
    industry = rows[0][2]
    
    # 获取财务数据
    cur2 = conn.execute(
        'SELECT report_date, roe, gross_margin, net_margin, revenue_yoy, profit_yoy, debt_ratio, net_profit, ocf_abs '
        'FROM financial_reports WHERE ts_code=? AND report_type="annual" AND fetch_success=1 '
        'ORDER BY report_date DESC LIMIT 1', (ts_code,))
    row = cur2.fetchone()
    if row:
        print(f'\n=== {name} ({ts_code}) 年报数据 ({row[0]}) ===')
        print(f'  ROE: {row[1]}%')
        print(f'  毛利率: {row[2]}%')
        print(f'  净利率: {row[3]}%')
        print(f'  营收同比: {row[4]}%')
        print(f'  净利同比: {row[5]}%')
        print(f'  负债率: {row[6]}%')
        print(f'  归母净利润: {row[7]}')
        print(f'  经营现金流: {row[8]}')
        
        if row[7] and row[8] and row[7] != 0:
            ocf_ratio = round(row[8] / row[7] * 100, 2)
            print(f'  OCF/净利润: {ocf_ratio}%')
        
        # 用全部股票重跑评分
        all_stocks_data = conn.execute(
            'SELECT s.ts_code, s.name, s.industry_l1, f.roe, f.gross_margin, f.net_margin, '
            'f.revenue_yoy, f.profit_yoy, f.debt_ratio, f.net_profit, f.ocf_abs '
            'FROM stocks s JOIN financial_reports f ON s.ts_code=f.ts_code '
            'WHERE f.report_type="annual" AND f.fetch_success=1 '
            'AND f.report_date = (SELECT MAX(report_date) FROM financial_reports WHERE ts_code=s.ts_code AND report_type="annual" AND fetch_success=1)'
        ).fetchall()
        
        all_stocks = []
        for r2 in all_stocks_data:
            all_stocks.append({
                'ts_code': r2[0], 'name': r2[1], 'industry_l1': r2[2],
                'roe': r2[3], 'gross_margin': r2[4], 'net_margin': r2[5],
                'revenue_yoy': r2[6], 'profit_yoy': r2[7], 'debt_ratio': r2[8],
                'net_profit': r2[9], 'ocf_abs': r2[10], 'fetch_success': True,
            })
        
        industry_groups = {}
        for s in all_stocks:
            ind = s.get('industry_l1', '未知')
            industry_groups.setdefault(ind, []).append(s)
        
        for s in all_stocks:
            if s['ts_code'] == ts_code:
                score = calc_score(s, industry_groups, all_stocks)
                print(f'\n=== 评分结果 ===')
                print(f'  总分: {score["total_score"]}  评级: {score["grade"]}')
                print(f'  盈利能力: {score["profit_score"]}  (你贴的Excel: 77)')
                print(f'  成长性: {score["growth_score"]}  (你贴的Excel: 92)')
                print(f'  现金流质量: {score["ocf_score"]}  (你贴的Excel: 80)')
                print(f'  偿债风险: {score["debt_score"]}  (你贴的Excel: 30)')
                
                ind = s.get('industry_l1', '未知')
                pool = industry_groups.get(ind, [])
                use_fallback = len(pool) < Config.MIN_INDUSTRY_SAMPLES
                print(f'\n行业: {ind}, 同行业池: {len(pool)}只, 全市场: {len(all_stocks)}只')
                if use_fallback:
                    print(f'  [注] 同行业样本不足{Config.MIN_INDUSTRY_SAMPLES}只，使用全市场对比 (折扣{Config.MARKET_FALLBACK_DISCOUNT})')
                break

conn.close()
