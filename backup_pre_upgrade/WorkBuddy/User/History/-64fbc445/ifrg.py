#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""快速测试单股数据流"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from datetime import datetime
from data_provider import DataProvider
from calculator import IndicatorCalculator
from scorer import Scorer
import pandas as pd

EVAL_DATE = datetime.today()
symbol = '600519'
print(f'Testing {symbol}...')

provider = DataProvider()
name = provider.get_stock_name(symbol)
print(f'Name: {name}')
industry = provider.get_industry(symbol)
print(f'Industry: {industry}')
quote = provider.get_stock_quote(symbol)
tmv = quote.get('total_mv', 0)
pe = quote.get('pe_ttm', 0)
print(f'Quote: total_mv={tmv:.0f}, pe={pe}')

df = provider.get_combined_financials(symbol)
print(f'Financials: {len(df)} rows')
if not df.empty:
    df_filtered = df[df['ann_date'] <= pd.Timestamp(EVAL_DATE)].copy()
    print(f'Filtered: {len(df_filtered)} rows')
    calc = IndicatorCalculator(df_filtered, eval_date=pd.Timestamp(EVAL_DATE))
    print(f'ROE: {calc.roe_ttm:.2f}, GM: {calc.gross_margin_ttm:.2f}')
    print(f'Rev YoY: {calc.q_revenue_yoy:.2f}, Profit YoY: {calc.q_net_profit_yoy:.2f}')
    print(f'DE: {calc.de_ratio:.2f}, Current: {calc.current_ratio:.2f}, ALR: {calc.asset_liability_ratio:.2f}')
    print(f'NP ratio: {calc.net_profit_ratio:.2f}, Cash recovery: {calc.cash_recovery_rate:.2f}')
    fcf_yield = calc.fcf_ttm / tmv if tmv > 0 else 0
    print(f'FCF yield: {fcf_yield:.4f}')
    scorer = Scorer(calc, quote, industry=industry)
    scores = scorer.total_score()
    print(f'Scores: growth={scores["growth"]:.2f}, profit={scores["profitability"]:.2f}, cash={scores["cash_flow"]:.2f}, leverage={scores["leverage"]:.2f}')
    print(f'Total: {scores["total_score"]:.2f}, Veto: {scores["veto"]}')
    annual = str(df_filtered[df_filtered['report_date'].dt.month == 12]['report_date'].max().date()) if len(df_filtered[df_filtered['report_date'].dt.month == 12]) > 0 else str(df_filtered['report_date'].max().date())
    print(f'Annual date: {annual}')
    print(f'Latest quarter: {str(df_filtered["report_date"].max().date())}')
print('DONE')
