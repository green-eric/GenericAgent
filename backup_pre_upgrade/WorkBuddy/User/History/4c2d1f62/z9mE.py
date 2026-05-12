#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""字段诊断：逐步追踪Excel每个字段从DB→计算→输出的完整链路"""
import sys
import pandas as pd
import numpy as np

# 测试股票
TEST_SYMBOLS = ['600519', '000858']
DB_PATH = r'd:\Project\ScoreSys\stock_data.db'

from database import StockDatabase
db = StockDatabase(DB_PATH)

for symbol in TEST_SYMBOLS:
    print(f"\n{'='*70}")
    print(f"  诊断股票: {symbol}")
    print(f"{'='*70}")

    # ===== Step 1: DB原始数据 =====
    df = db.get_financials(symbol)
    if df is None or df.empty:
        print(f"  [SKIP] {symbol} 无DB数据")
        continue

    print(f"\n--- Step 1: DB原始数据 ({len(df)}行) ---")
    print(f"  列名: {list(df.columns)}")
    print(f"  dtypes:\n{df.dtypes.to_string()}")
    
    # 关键列检查
    key_cols = ['equity_parent', 'total_assets', 'total_liab', 'total_equity',
                'current_assets', 'current_liab', 'net_profit_parent', 'net_profit_ex',
                'revenue', 'oper_cost', 'oper_profit', 'ocf', 'capex', 'cash_from_sales',
                'fin_expense', 'ann_date', 'report_date']
    for col in key_cols:
        if col in df.columns:
            vals = df[col].dropna()
            nonzero = (vals != 0).sum() if len(vals) > 0 else 0
            print(f"  {col:25s}: 非空={len(vals):>3}/{len(df)}  非零={nonzero:>3}  最新3值={list(df[col].tail(3).values)}")
        else:
            print(f"  {col:25s}: *** 缺失! ***")

    # ===== Step 2: 日期转换 =====
    if not pd.api.types.is_datetime64_any_dtype(df['report_date']):
        df['report_date'] = pd.to_datetime(df['report_date'], errors='coerce')
    if 'ann_date' in df.columns and not pd.api.types.is_datetime64_any_dtype(df['ann_date']):
        df['ann_date'] = pd.to_datetime(df['ann_date'], errors='coerce')
    
    eval_date = pd.Timestamp.now()
    df_filtered = df[df['ann_date'] <= eval_date].copy()
    print(f"\n--- Step 2: 日期过滤 ---")
    print(f"  原始: {len(df)}行 → 过滤后: {len(df_filtered)}行 (eval_date={eval_date.date()})")

    # ===== Step 3: Calculator 计算 =====
    if len(df_filtered) < 4:
        print(f"  [SKIP] 数据不足4个季度")
        continue

    from calculator import IndicatorCalculator
    calc = IndicatorCalculator(df_filtered, eval_date=eval_date)
    
    print(f"\n--- Step 3: Calculator 输出 ---")
    metrics = calc.get_metrics()
    for k, v in metrics.items():
        print(f"  {k:25s} = {v}")

    # ===== Step 4: 检查关键中间值 =====
    print(f"\n--- Step 4: 关键中间值 ---")
    print(f"  _ttm_net_profit   = {calc._ttm_net_profit}")
    print(f"  _equity_parent    = {calc._equity_parent}")
    print(f"  _ttm_revenue      = {calc._ttm_revenue}")
    print(f"  _ttm_ocf          = {calc._ttm_ocf}")
    print(f"  _ttm_capex        = {calc._ttm_capex}")
    print(f"  _ttm_oper_cost    = {calc._ttm_oper_cost}")
    print(f"  _ttm_cash_sales   = {calc._ttm_cash_sales}")
    print(f"  _ttm_fin_expense  = {calc._ttm_fin_expense}")
    print(f"  _ttm_oper_profit  = {calc._ttm_oper_profit}")
    print(f"  _total_assets     = {calc._total_assets}")
    print(f"  _total_liab       = {calc._total_liab}")
    print(f"  _total_equity     = {calc._total_equity}")
    print(f"  _current_assets   = {calc._current_assets}")
    print(f"  _current_liab     = {calc._current_liab}")
    print(f"  _use_ex_profit    = {calc._use_ex_profit}")
    print(f"  q_net_profit_yoy  = {calc.q_net_profit_yoy}")
    print(f"  q_revenue_yoy     = {calc.q_revenue_yoy}")

    # ===== Step 5: Scorer 评分 =====
    quote = db.get_quote(symbol)
    print(f"\n--- Step 5: Quote数据 ---")
    print(f"  total_mv = {quote.get('total_mv', 0)}")
    print(f"  pe_ttm   = {quote.get('pe_ttm', 0)}")

    stock_info = db.get_stock_info(symbol)
    name = stock_info.get('name', symbol) if stock_info else symbol
    industry = stock_info.get('industry', None) if stock_info else None
    print(f"  name     = {name}")
    print(f"  industry = {industry}")

    from scorer import Scorer
    scorer = Scorer(calc, quote, industry=industry)
    scores = scorer.total_score()

    print(f"\n--- Step 6: Scorer 输出 ---")
    for k, v in scores.items():
        print(f"  {k:25s} = {v}")

    # ===== Step 7: Excel字段映射验证 =====
    print(f"\n--- Step 7: Excel字段值 ---")
    res = {
        'symbol': symbol, 'name': name, 'industry': industry or '',
        'q_revenue_yoy': round(calc.q_revenue_yoy, 2),
        'q_net_profit_yoy': round(calc.q_net_profit_yoy, 2),
        'roe_ttm': round(calc.roe_ttm, 2),
        'gross_margin_ttm': round(calc.gross_margin_ttm, 2),
        'net_profit_ratio': round(calc.net_profit_ratio, 2),
        'fcf_yield': round(calc.fcf_ttm / quote.get('total_mv', 1) if quote.get('total_mv', 0) > 0 else 0, 4),
        'cash_recovery_rate': round(calc.cash_recovery_rate, 2),
        'de_ratio': round(calc.de_ratio, 2),
        'current_ratio': round(calc.current_ratio, 2),
        'asset_liability_ratio': round(calc.asset_liability_ratio, 2),
        'pe_ttm': round(quote.get('pe_ttm', 0), 2),
        'total_mv': round(quote.get('total_mv', 0) / 100000000, 2),
        'total_score': scores['total_score'],
        'rating': 'A+' if scores['total_score'] >= 80 else 'A' if scores['total_score'] >= 70 else 'B+' if scores['total_score'] >= 60 else 'B' if scores['total_score'] >= 50 else 'C' if scores['total_score'] >= 40 else 'D',
        'profitability': round(scores['profitability'], 2),
        'growth': round(scores['growth'], 2),
        'cash_flow_quality': round(scores['cash_flow'], 2),
        'leverage_risk': round(scores['leverage'], 2),
        'veto': '是' if scores['veto'] else '否',
        'veto_reason': scores.get('veto_reason', ''),
    }
    
    # 标记为0的字段
    zero_fields = []
    for k, v in res.items():
        is_zero = (v == 0 or v == 0.0 or v == '0')
        flag = ' <<< ZERO!' if is_zero else ''
        print(f"  {k:25s} = {v}{flag}")
        if is_zero and k not in ['veto_reason']:
            zero_fields.append(k)
    
    if zero_fields:
        print(f"\n  *** 为0的字段: {zero_fields} ***")
    else:
        print(f"\n  *** 所有字段均有值! ***")

print(f"\n{'='*70}")
print("诊断完成")
