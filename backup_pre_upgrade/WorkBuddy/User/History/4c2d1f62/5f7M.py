#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""字段诊断：逐步追踪Excel每个字段从DB→计算→输出的完整链路"""
import sys
import pandas as pd
import numpy as np

# 测试股票
TEST_SYMBOLS = ['600519', '000858']
DB_PATH = r'd:\Project\ScoreSys\stock_data_test.db'

from database import StockDatabase
db = StockDatabase(DB_PATH)

all_zero_fields = {}

for symbol in TEST_SYMBOLS:
    print(f"\n{'='*70}")
    print(f"  诊断股票: {symbol}")
    print(f"{'='*70}")

    df = db.get_financials(symbol)
    if df is None or df.empty:
        print(f"  [SKIP] {symbol} 无DB数据")
        continue

    # 日期转换
    if not pd.api.types.is_datetime64_any_dtype(df['report_date']):
        df['report_date'] = pd.to_datetime(df['report_date'], errors='coerce')
    if 'ann_date' in df.columns and not pd.api.types.is_datetime64_any_dtype(df['ann_date']):
        df['ann_date'] = pd.to_datetime(df['ann_date'], errors='coerce')
    
    eval_date = pd.Timestamp.now()
    df_filtered = df[df['ann_date'] <= eval_date].copy()

    if len(df_filtered) < 4:
        print(f"  [SKIP] 数据不足4个季度")
        continue

    from calculator import IndicatorCalculator
    calc = IndicatorCalculator(df_filtered, eval_date=eval_date)

    # Quote & Stock Info
    quote = db.get_quote(symbol)
    stock_info = db.get_stock_info(symbol)
    name = stock_info.get('name', symbol) if stock_info else symbol
    industry = stock_info.get('industry', None) if stock_info else None

    from scorer import Scorer
    scorer = Scorer(calc, quote, industry=industry)
    scores = scorer.total_score()

    # 关键中间值
    print(f"\n--- 关键中间值 ---")
    print(f"  _ttm_net_profit   = {calc._ttm_net_profit:,.2f}")
    print(f"  _ttm_revenue      = {calc._ttm_revenue:,.2f}")
    print(f"  _ttm_ocf          = {calc._ttm_ocf:,.2f}")
    print(f"  _equity_parent    = {calc._equity_parent:,.2f}")
    print(f"  _ttm_fin_expense  = {calc._ttm_fin_expense:,.2f}")
    print(f"  _use_ex_profit    = {calc._use_ex_profit}")
    print(f"  total_mv          = {quote.get('total_mv',0):,.0f}")
    print(f"  pe_ttm            = {quote.get('pe_ttm',0):.1f}")

    # Excel字段值
    res = {
        'symbol': symbol, 'name': name, 'industry': industry or '',
        'q_revenue_yoy': round(calc.q_revenue_yoy, 2),
        'q_net_profit_yoy': round(calc.q_net_profit_yoy, 2),
        'roe_ttm': round(calc.roe_ttm, 2),
        'gross_margin_ttm': round(calc.gross_margin_ttm, 2),
        'net_margin_ttm': round(calc.net_margin_ttm, 2),
        'net_profit_ratio': round(calc.net_profit_ratio, 2),
        'fcf_yield': round(calc.fcf_ttm / quote.get('total_mv', 1) if quote.get('total_mv', 0) > 0 else 0, 4),
        'cash_recovery_rate': round(calc.cash_recovery_rate, 2),
        'de_ratio': round(calc.de_ratio, 2),
        'current_ratio': round(calc.current_ratio, 2),
        'asset_liability_ratio': round(calc.asset_liability_ratio, 2),
        'interest_cover': round(calc.interest_cover, 2),
        'pe_ttm': round(quote.get('pe_ttm', 0), 2),
        'total_mv': round(quote.get('total_mv', 0) / 100000000, 2),
        'total_score': scores['total_score'],
        'profitability': round(scores['profitability'], 2),
        'growth': round(scores['growth'], 2),
        'cash_flow_quality': round(scores['cash_flow'], 2),
        'leverage_risk': round(scores['leverage'], 2),
        'veto': '是' if scores['veto'] else '否',
    }

    # 标记异常字段
    zero_fields = []
    expected_nonzero = ['roe_ttm', 'gross_margin_ttm', 'net_margin_ttm', 'net_profit_ratio',
                        'cash_recovery_rate', 'de_ratio', 'current_ratio', 'asset_liability_ratio',
                        'pe_ttm', 'total_mv', 'total_score', 'profitability', 'cash_flow_quality',
                        'leverage_risk', 'interest_cover']
    
    print(f"\n--- Excel字段值 ---")
    for k, v in res.items():
        is_zero = (v == 0 or v == 0.0 or v == '0')
        is_expected = k in expected_nonzero
        flag = ''
        if is_zero and is_expected:
            flag = ' <<< ZERO! (should be non-zero)'
            zero_fields.append(k)
        elif is_zero and not is_expected:
            flag = ' (zero OK - negative growth)'
        print(f"  {k:25s} = {v}{flag}")
    
    all_zero_fields[symbol] = zero_fields

print(f"\n{'='*70}")
print(f"  总结：应为非零但为0的字段")
print(f"{'='*70}")
for sym, fields in all_zero_fields.items():
    if fields:
        print(f"  {sym}: {fields}")
    else:
        print(f"  {sym}: ALL OK! 所有字段非零")

# 运行完整的from-db评分
print(f"\n{'='*70}")
print(f"  from-db评分测试")
print(f"{'='*70}")
