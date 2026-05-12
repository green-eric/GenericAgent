#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
步骤2：Excel字段验证
对比API原始值与评分输出值，确保数据取值准确
输出：validate_fields.xlsx，包含：
  - Sheet1: 原始API数据
  - Sheet2: 计算指标
  - Sheet3: 评分结果
  - Sheet4: 字段对比（API原始值 vs Excel输出值）
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ['PYTHONIOENCODING'] = 'utf-8'

import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

import pandas as pd
import json
from datetime import datetime
from data_provider import DataProvider, _neodata_query
from calculator import IndicatorCalculator
from scorer import Scorer
from config import WEIGHTS, THRESHOLDS

def analyze_stock(symbol):
    """获取单只股票的完整数据链"""
    print(f"\n{'='*50}")
    print(f"分析 {symbol}")
    print(f"{'='*50}")
    
    provider = DataProvider()
    
    # 1. 基础信息
    name = provider.get_stock_name(symbol)
    industry = provider.get_industry(symbol)
    quote = provider.get_stock_quote(symbol)
    
    print(f"  名称: {name}")
    print(f"  行业: {industry}")
    print(f"  总市值: {quote['total_mv']/1e8:,.2f}亿")
    print(f"  PE-TTM: {quote['pe_ttm']}")
    
    # 2. 财务数据
    df = provider.get_combined_financials(symbol)
    if df.empty:
        print(f"  ❌ 无财务数据")
        return None
    
    print(f"  财务数据: {len(df)} 条记录")
    print(f"  报告期范围: {df['report_date'].min().date()} ~ {df['report_date'].max().date()}")
    
    # 3. 计算指标
    eval_date = datetime.today()
    calc = IndicatorCalculator(df, eval_date=pd.Timestamp(eval_date))
    
    print(f"\n  --- 计算指标 ---")
    print(f"  ROE(TTM): {calc.roe_ttm:.2f}%")
    print(f"  毛利率(TTM): {calc.gross_margin_ttm:.2f}%")
    print(f"  营收同比(单季): {calc.q_revenue_yoy:.2f}%")
    print(f"  净利润同比(单季): {calc.q_net_profit_yoy:.2f}%")
    print(f"  净现比: {calc.net_profit_ratio:.2f}")
    print(f"  FCF(TTM): {calc.fcf_ttm/1e8:,.2f}亿")
    print(f"  收现比: {calc.cash_recovery_rate:.2f}")
    print(f"  D/E: {calc.de_ratio:.2f}")
    print(f"  流动比率: {calc.current_ratio:.2f}")
    print(f"  资产负债率: {calc.asset_liability_ratio:.2f}%")
    
    # 4. 评分
    scorer = Scorer(calc, quote, industry=industry)
    scores = scorer.total_score()
    
    fcf_yield = (calc.fcf_ttm / quote['total_mv']) if quote.get('total_mv', 0) > 0 else 0
    
    print(f"\n  --- 评分结果 ---")
    print(f"  成长性: {scores['growth']:.2f}")
    print(f"  盈利能力: {scores['profitability']:.2f}")
    print(f"  现金流质量: {scores['cash_flow']:.2f}")
    print(f"  偿债风险: {scores['leverage']:.2f}")
    print(f"  估值: {scores['valuation']:.2f}")
    print(f"  总分: {scores['total_score']:.2f}")
    print(f"  否决: {scores.get('veto', False)}")
    
    # 5. 构建完整结果
    annual = df[df['report_date'].dt.month == 12]
    annual_date = str(annual['report_date'].max().date()) if len(annual) > 0 else str(df['report_date'].max().date())
    
    result = {
        'symbol': symbol,
        'name': name,
        'industry': industry,
        'total_mv_yuan': quote['total_mv'],
        'total_mv_yi': round(quote['total_mv'] / 1e8, 2),
        'pe_ttm': quote['pe_ttm'],
        'roe_ttm': round(calc.roe_ttm, 2),
        'gross_margin_ttm': round(calc.gross_margin_ttm, 2),
        'q_revenue_yoy': round(calc.q_revenue_yoy, 2),
        'q_net_profit_yoy': round(calc.q_net_profit_yoy, 2),
        'net_profit_ratio': round(calc.net_profit_ratio, 2),
        'fcf_ttm_yuan': calc.fcf_ttm,
        'fcf_yield': round(fcf_yield, 4),
        'cash_recovery_rate': round(calc.cash_recovery_rate, 2),
        'de_ratio': round(calc.de_ratio, 2),
        'current_ratio': round(calc.current_ratio, 2),
        'asset_liability_ratio': round(calc.asset_liability_ratio, 2),
        'annual_report_date': annual_date,
        'latest_quarter': str(df['report_date'].max().date()),
        'data_completeness': min(len(df) / 8 * 100, 100),
        'growth_score': round(scores['growth'], 2),
        'profitability_score': round(scores['profitability'], 2),
        'cashflow_score': round(scores['cash_flow'], 2),
        'leverage_score': round(scores['leverage'], 2),
        'valuation_score': round(scores['valuation'], 2),
        'total_score': scores['total_score'],
        'veto': '是' if scores.get('veto', False) else '否',
        'veto_reason': scores.get('veto_reason', ''),
        # 原始财务数据（最近4期）
        'raw_financials': df.tail(4).to_dict('records'),
    }
    
    return result


def build_comparison_sheet(results):
    """构建字段对比表"""
    rows = []
    field_map = [
        ('股票代码', 'symbol'),
        ('股票名称', 'name'),
        ('行业', 'industry'),
        ('总市值(亿)', 'total_mv_yi'),
        ('PE-TTM', 'pe_ttm'),
        ('ROE(TTM)%', 'roe_ttm'),
        ('毛利率(TTM)%', 'gross_margin_ttm'),
        ('营收同比(单季)%', 'q_revenue_yoy'),
        ('净利润同比(单季)%', 'q_net_profit_yoy'),
        ('净现比', 'net_profit_ratio'),
        ('FCF收益率', 'fcf_yield'),
        ('收现比', 'cash_recovery_rate'),
        ('D/E', 'de_ratio'),
        ('流动比率', 'current_ratio'),
        ('资产负债率%', 'asset_liability_ratio'),
        ('成长性得分', 'growth_score'),
        ('盈利能力得分', 'profitability_score'),
        ('现金流得分', 'cashflow_score'),
        ('偿债风险得分', 'leverage_score'),
        ('估值得分', 'valuation_score'),
        ('总分', 'total_score'),
        ('触发否决', 'veto'),
        ('否决原因', 'veto_reason'),
    ]
    
    for label, key in field_map:
        row = {'字段': label}
        for r in results:
            row[r['symbol']] = r.get(key, '')
        rows.append(row)
    
    return pd.DataFrame(rows)


def main():
    print("=" * 60)
    print("步骤2：Excel字段验证")
    print("=" * 60)
    
    symbols = ['600519', '000858']
    results = []
    
    for symbol in symbols:
        r = analyze_stock(symbol)
        if r:
            results.append(r)
    
    if not results:
        print("\n❌ 无有效结果")
        return
    
    # 输出Excel
    output_file = 'validate_fields.xlsx'
    
    with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
        # Sheet1: 字段对比
        comp_df = build_comparison_sheet(results)
        comp_df.to_excel(writer, sheet_name='字段对比', index=False)
        
        # Sheet2: 评分结果（模拟main.py输出格式）
        score_rows = []
        for r in results:
            score_rows.append({
                '股票代码': r['symbol'],
                '股票名称': r['name'],
                '行业': r['industry'],
                '总分': r['total_score'],
                '成长性': r['growth_score'],
                '盈利能力': r['profitability_score'],
                '现金流质量': r['cashflow_score'],
                '偿债风险': r['leverage_score'],
                '估值': r['valuation_score'],
                'ROE(TTM)': r['roe_ttm'],
                '毛利率(TTM)': r['gross_margin_ttm'],
                '营收同比': r['q_revenue_yoy'],
                '净利润同比': r['q_net_profit_yoy'],
                '净现比': r['net_profit_ratio'],
                'FCF收益率': r['fcf_yield'],
                '收现比': r['cash_recovery_rate'],
                'D/E': r['de_ratio'],
                '流动比率': r['current_ratio'],
                '资产负债率': r['asset_liability_ratio'],
                'PE-TTM': r['pe_ttm'],
                '总市值(亿)': r['total_mv_yi'],
                '触发否决': r['veto'],
                '否决原因': r['veto_reason'],
            })
        pd.DataFrame(score_rows).to_excel(writer, sheet_name='评分结果', index=False)
        
        # Sheet3: 原始财务数据
        for r in results:
            if r.get('raw_financials'):
                df_raw = pd.DataFrame(r['raw_financials'])
                sheet_name = f"{r['symbol']}_财务数据"
                df_raw.to_excel(writer, sheet_name=sheet_name[:31], index=False)
    
    print(f"\n✅ 验证结果已保存: {output_file}")
    print(f"   包含 {len(results)} 只股票的完整数据链")
    
    # 打印关键字段对比
    print("\n" + "=" * 60)
    print("关键字段验证")
    print("=" * 60)
    for r in results:
        print(f"\n  [{r['symbol']} {r['name']}]")
        print(f"    总市值: {r['total_mv_yi']:,.2f}亿  PE-TTM: {r['pe_ttm']}")
        print(f"    ROE: {r['roe_ttm']}%  毛利率: {r['gross_margin_ttm']}%")
        print(f"    营收同比: {r['q_revenue_yoy']}%  净利润同比: {r['q_net_profit_yoy']}%")
        print(f"    净现比: {r['net_profit_ratio']}  FCF收益率: {r['fcf_yield']:.4f}")
        print(f"    D/E: {r['de_ratio']}  流动比率: {r['current_ratio']}  资产负债率: {r['asset_liability_ratio']}%")
        print(f"    总分: {r['total_score']}  (成长{r['growth_score']}/盈利{r['profitability_score']}/现金流{r['cashflow_score']}/偿债{r['leverage_score']}/估值{r['valuation_score']})")


if __name__ == '__main__':
    main()
