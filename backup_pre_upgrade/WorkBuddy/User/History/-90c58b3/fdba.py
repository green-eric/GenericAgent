#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================================
 Excel 字段验证脚本
 对比 API 原始值 vs 评分输出值，确保数据取值准确
 测试股票：600519（贵州茅台）、000858（五粮液）
================================================================================
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from datetime import datetime
from data_provider import DataProvider
from calculator import IndicatorCalculator
from scorer import Scorer
from main import batch_evaluate, save_to_excel, EXCEL_COLUMNS
import pandas as pd

TEST_STOCKS = ['600519', '000858']
EVAL_DATE = datetime.today()


def fetch_raw_api_values(symbol):
    """直接从API获取原始值，作为基准"""
    print(f"\n{'='*60}")
    print(f"  API 原始值采集: {symbol}")
    print(f"{'='*60}")
    
    provider = DataProvider()
    
    # 1. 基础信息
    name = provider.get_stock_name(symbol)
    industry = provider.get_industry(symbol)
    print(f"  名称: {name}")
    print(f"  行业: {industry}")
    
    # 2. 行情
    quote = provider.get_stock_quote(symbol)
    total_mv_raw = quote.get('total_mv', 0)
    pe_ttm_raw = quote.get('pe_ttm', 0)
    print(f"  总市值(元): {total_mv_raw:,.0f}")
    print(f"  总市值(亿): {total_mv_raw / 1e8:,.2f}")
    print(f"  PE-TTM: {pe_ttm_raw}")
    
    # 3. 财务数据
    df = provider.get_combined_financials(symbol)
    if df.empty:
        print(f"  [ERROR] 无财务数据")
        return None
    
    # 防未来函数过滤
    df_filtered = df[df['ann_date'] <= pd.Timestamp(EVAL_DATE)].copy()
    print(f"  财报期数: {len(df_filtered)} (过滤后)")
    
    # 4. 计算指标
    calc = IndicatorCalculator(df_filtered, eval_date=pd.Timestamp(EVAL_DATE))
    
    print(f"\n  --- 计算指标 ---")
    print(f"  ROE(TTM): {calc.roe_ttm:.2f}%")
    print(f"  毛利率(TTM): {calc.gross_margin_ttm:.2f}%")
    print(f"  营收同比(单季): {calc.q_revenue_yoy:.2f}%")
    print(f"  净利润同比(单季): {calc.q_net_profit_yoy:.2f}%")
    print(f"  资产负债率: {calc.asset_liability_ratio:.2f}%")
    print(f"  D/E: {calc.de_ratio:.2f}")
    print(f"  流动比率: {calc.current_ratio:.2f}")
    print(f"  净现比: {calc.net_profit_ratio:.2f}")
    print(f"  收现比: {calc.cash_recovery_rate:.2f}")
    print(f"  OCF(TTM): {calc.ocf_ttm:,.0f}")
    print(F"  FCF(TTM): {calc.fcf_ttm:,.0f}")
    
    # FCF Yield
    fcf_yield_raw = calc.fcf_ttm / total_mv_raw if total_mv_raw > 0 else 0
    print(f"  FCF收益率: {fcf_yield_raw:.4f}")
    
    # 5. 评分
    scorer = Scorer(calc, quote, industry=industry)
    scores = scorer.total_score()
    
    print(f"\n  --- 评分结果 ---")
    print(f"  成长性: {scores['growth']:.2f}")
    print(f"  盈利能力: {scores['profitability']:.2f}")
    print(f"  现金流质量: {scores['cash_flow']:.2f}")
    print(f"  偿债风险: {scores['leverage']:.2f}")
    print(f"  估值: {scores['valuation']:.2f}")
    print(f"  总分: {scores['total_score']:.2f}")
    print(f"  否决: {'是' if scores['veto'] else '否'} {scores.get('veto_reason', '')}")
    
    # 日期
    annual_date = str(df_filtered[df_filtered['report_date'].dt.month == 12]['report_date'].max().date()) if len(df_filtered[df_filtered['report_date'].dt.month == 12]) > 0 else str(df_filtered['report_date'].max().date())
    latest_quarter = str(df_filtered['report_date'].max().date()) if hasattr(df_filtered['report_date'].max(), 'date') else str(df_filtered['report_date'].max())
    
    return {
        'symbol': symbol,
        'name': name,
        'industry': industry or '',
        'total_mv_yuan': total_mv_raw,
        'total_mv_yi': round(total_mv_raw / 1e8, 2),
        'pe_ttm': round(pe_ttm_raw, 2),
        'roe_ttm': round(calc.roe_ttm, 2),
        'gross_margin_ttm': round(calc.gross_margin_ttm, 2),
        'q_revenue_yoy': round(calc.q_revenue_yoy, 2),
        'q_net_profit_yoy': round(calc.q_net_profit_yoy, 2),
        'asset_liability_ratio': round(calc.asset_liability_ratio, 2),
        'de_ratio': round(calc.de_ratio, 2),
        'current_ratio': round(calc.current_ratio, 2),
        'net_profit_ratio': round(calc.net_profit_ratio, 2),
        'cash_recovery_rate': round(calc.cash_recovery_rate, 2),
        'fcf_yield': round(fcf_yield_raw, 4),
        'growth': round(scores['growth'], 2),
        'profitability': round(scores['profitability'], 2),
        'cash_flow': round(scores['cash_flow'], 2),
        'leverage': round(scores['leverage'], 2),
        'valuation': round(scores['valuation'], 2),
        'total_score': scores['total_score'],
        'veto': '是' if scores['veto'] else '否',
        'veto_reason': scores.get('veto_reason', ''),
        'annual_report_date': annual_date,
        'latest_quarter': latest_quarter,
        'completeness': min(len(df_filtered) / 8 * 100, 100),
    }


def compare_results(symbol, raw, output):
    """对比原始值和输出值"""
    print(f"\n{'='*60}")
    print(f"  字段对比: {symbol}")
    print(f"{'='*60}")
    print(f"  {'字段':<25} {'API原始值':>15} {'输出值':>15} {'状态':>8}")
    print(f"  {'-'*65}")
    
    FIELD_MAP = [
        ('name', '股票名称'),
        ('industry', '行业'),
        ('total_mv_yi', '总市值(亿)'),
        ('pe_ttm', 'PE-TTM'),
        ('roe_ttm', 'ROE(TTM)%'),
        ('gross_margin_ttm', '毛利率(TTM)%'),
        ('q_revenue_yoy', '营收同比%'),
        ('q_net_profit_yoy', '净利润同比%'),
        ('asset_liability_ratio', '资产负债率%'),
        ('de_ratio', 'D/E'),
        ('current_ratio', '流动比率'),
        ('net_profit_ratio', '净现比'),
        ('cash_recovery_rate', '收现比'),
        ('fcf_yield', 'FCF收益率'),
        ('growth', '成长性评分'),
        ('profitability', '盈利能力评分'),
        ('cash_flow', '现金流评分'),
        ('leverage', '偿债风险评分'),
        ('total_score', '总分'),
        ('annual_report_date', '年报日期'),
        ('latest_quarter', '最新季报期'),
    ]
    
    all_ok = True
    for field, label in FIELD_MAP:
        raw_val = raw.get(field, 'N/A')
        out_val = output.get(field, 'N/A')
        
        # 数值比较（允许0.05的浮点误差）
        if isinstance(raw_val, (int, float)) and isinstance(out_val, (int, float)):
            match = abs(raw_val - out_val) < 0.05
        else:
            match = str(raw_val) == str(out_val)
        
        status = '✅' if match else '❌'
        if not match:
            all_ok = False
        
        print(f"  {label:<25} {str(raw_val):>15} {str(out_val):>15} {status:>8}")
    
    print(f"\n  {'全部通过 ✅' if all_ok else '存在差异 ❌ 请检查!'}")
    return all_ok


def main():
    print("=" * 60)
    print("  Excel 字段验证脚本")
    print(f"  测试股票: {', '.join(TEST_STOCKS)}")
    print(f"  评估日期: {EVAL_DATE.date()}")
    print("=" * 60)
    
    # Step 1: 获取API原始值
    raw_values = {}
    for symbol in TEST_STOCKS:
        raw = fetch_raw_api_values(symbol)
        if raw:
            raw_values[symbol] = raw
    
    if not raw_values:
        print("\n[ERROR] 无法获取API原始值，终止验证")
        return False
    
    # Step 2: 运行评分流程获取输出
    print(f"\n{'='*60}")
    print(f"  运行评分流程 (batch_evaluate)")
    print(f"{'='*60}")
    
    results = batch_evaluate(TEST_STOCKS, EVAL_DATE, mock=False, workers=2, rate_limit=0.5)
    
    if not results:
        print("\n[ERROR] 评分流程无输出，终止验证")
        return False
    
    # Step 3: 逐个对比
    all_pass = True
    for symbol in TEST_STOCKS:
        if symbol not in raw_values:
            continue
        
        # 找到对应的输出结果
        output = None
        for r in results:
            if r.get('symbol') == symbol:
                output = r
                break
        
        if not output:
            print(f"\n[WARNING] {symbol} 无评分输出，跳过对比")
            all_pass = False
            continue
        
        passed = compare_results(symbol, raw_values[symbol], output)
        if not passed:
            all_pass = False
    
    # Step 4: 总结
    print(f"\n{'='*60}")
    if all_pass:
        print("  ✅ 所有字段验证通过！数据取值准确。")
    else:
        print("  ❌ 部分字段存在差异，请检查上方标记为 ❌ 的字段。")
    print(f"{'='*60}")
    
    return all_pass


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
