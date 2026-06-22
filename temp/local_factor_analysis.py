#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""本地数据资产盘点 & 因子有效性分析
基于stock_data.db(1.76GB) + wq101因子数据
只读操作，绝不写入stock_data.db"""
import sqlite3, pandas as pd, numpy as np, json, sys, io, os
from datetime import datetime

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
DB_PATH = "./data/stock_data.db"
os.makedirs("./analysis_output", exist_ok=True)

conn = sqlite3.connect(DB_PATH)

# === Step 1: 数据概览 ===
print("=" * 60)
print("📊 Step 1: 数据概览")
print("=" * 60)

quotes_stats = pd.read_sql("""
    SELECT COUNT(*) as total_rows,
           COUNT(DISTINCT symbol) as total_stocks,
           MIN(trade_date) as min_date,
           MAX(trade_date) as max_date,
           AVG(close_price) as avg_close
    FROM quotes
""", conn)
print(f"行情: {quotes_stats['total_rows'].iloc[0]:,}行, {quotes_stats['total_stocks'].iloc[0]}只")
print(f"时间: {quotes_stats['min_date'].iloc[0]} ~ {quotes_stats['max_date'].iloc[0]}")

scores_stats = pd.read_sql("""
    SELECT rating, COUNT(*) as cnt, AVG(total_score) as avg_score, AVG(data_completeness) as avg_comp
    FROM scores GROUP BY rating ORDER BY rating
""", conn)
print("\n评分分布:")
for _, row in scores_stats.iterrows():
    print(f"  {row['rating']}: {row['cnt']}只 (均分{row['avg_score']:.1f}, 完整度{row['avg_comp']:.2f})")

# === Step 2: 因子IC分析 ===
print("\n" + "=" * 60)
print("📊 Step 2: 因子IC分析 (scores维度 vs 未来收益)")
print("=" * 60)

# 获取月度收益
monthly_ret = pd.read_sql("""
    WITH monthly_data AS (
        SELECT symbol,
               strftime('%Y-%m', trade_date) as month,
               MIN(trade_date) as first_date,
               MAX(trade_date) as last_date
        FROM quotes
        WHERE trade_date >= '2025-01-01' AND trade_date <= '2025-12-31'
        GROUP BY symbol, strftime('%Y-%m', trade_date)
    ),
    first_prices AS (
        SELECT m.symbol, m.month, q.close_price as first_close
        FROM monthly_data m
        JOIN quotes q ON q.symbol = m.symbol AND q.trade_date = m.first_date
    ),
    last_prices AS (
        SELECT m.symbol, m.month, q.close_price as last_close
        FROM monthly_data m
        JOIN quotes q ON q.symbol = m.symbol AND q.trade_date = m.last_date
    )
    SELECT f.symbol, f.month, f.first_close, l.last_close,
           (l.last_close - f.first_close) / f.first_close as monthly_ret
    FROM first_prices f
    JOIN last_prices l ON f.symbol = l.symbol AND f.month = l.month
""", conn)
print(f"月度收益: {len(monthly_ret)}行, {monthly_ret['symbol'].nunique()}只")

# 取最近3月平均收益
recent_ret = monthly_ret[monthly_ret['month'] >= '2025-10'].groupby('symbol')['monthly_ret'].mean().reset_index()
print(f"最近3月收益: {len(recent_ret)}只")

# scores表因子
factor_cols = ['growth', 'profitability', 'cash_flow', 'leverage', 'valuation', 'momentum', 'industry_momentum', 'reversal', 'turnover']
scores = pd.read_sql(f"SELECT symbol, total_score, {','.join(factor_cols)} FROM scores", conn)
merged = scores.merge(recent_ret, on='symbol', how='inner')
print(f"合并样本: {len(merged)}只")

ic_results = []
for f in factor_cols:
    valid = merged[[f, 'monthly_ret']].dropna()
    if len(valid) > 10:
        ic = valid[f].corr(valid['monthly_ret'])
        ic_results.append({'factor': f, 'ic': ic, 'abs_ic': abs(ic), 'n': len(valid)})

ic_df = pd.DataFrame(ic_results).sort_values('abs_ic', ascending=False)
print(f"\n{'因子':<20} {'IC':>8} {'|IC|':>8} {'样本':>6}")
print("-" * 46)
for _, row in ic_df.iterrows():
    print(f"{row['factor']:<20} {row['ic']:>8.4f} {row['abs_ic']:>8.4f} {row['n']:>6}")

# === Step 3: 因子冗余 ===
print("\n" + "=" * 60)
print("📊 Step 3: 因子冗余分析")
print("=" * 60)

corr_data = merged[factor_cols].corr()
high_corr = []
for i in range(len(factor_cols)):
    for j in range(i+1, len(factor_cols)):
        c = corr_data.iloc[i, j]
        if abs(c) > 0.5:
            high_corr.append({'f1': factor_cols[i], 'f2': factor_cols[j], 'corr': c})
high_corr_df = pd.DataFrame(high_corr).sort_values('corr', key=abs, ascending=False)
print(f"高相关因子对 (|r|>0.5): {len(high_corr_df)}对")
for _, row in high_corr_df.head(10).iterrows():
    print(f"  {row['f1']:<20} <-> {row['f2']:<20} r={row['corr']:>7.4f}")

# === Step 4: 综合排名 ===
print("\n" + "=" * 60)
print("📊 Step 4: 综合排名")
print("=" * 60)

summary = []
for _, row in ic_df.iterrows():
    f = row['factor']
    avg_cross = corr_data[f].abs().mean()
    summary.append({
        'factor': f, 'ic': row['ic'], 'abs_ic': row['abs_ic'],
        'avg_cross_corr': avg_cross, 'independence': 1 - avg_cross
    })
summary_df = pd.DataFrame(summary).sort_values('abs_ic', ascending=False)
print(f"{'因子':<20} {'IC':>8} {'独立性':>8} {'推荐':>4}")
print("-" * 44)
for _, row in summary_df.iterrows():
    rec = '⭐' if row['abs_ic'] > 0.05 else '  '
    print(f"{row['factor']:<20} {row['ic']:>8.4f} {row['independence']:>8.4f} {rec:>4}")

# === 保存 ===
conn.close()
output = {
    'timestamp': datetime.now().isoformat(),
    'data_summary': {
        'total_quotes': int(quotes_stats['total_rows'].iloc[0]),
        'total_stocks': int(quotes_stats['total_stocks'].iloc[0]),
        'date_range': f"{quotes_stats['min_date'].iloc[0]} ~ {quotes_stats['max_date'].iloc[0]}",
    },
    'ic_ranking': ic_df.to_dict('records'),
    'high_corr_pairs': high_corr_df.to_dict('records'),
    'factor_summary': summary_df.to_dict('records'),
}
with open('./analysis_output/factor_analysis_results.json', 'w', encoding='utf-8') as f:
    json.dump(output, f, ensure_ascii=False, indent=2)

print(f"\n✅ 结果已保存: analysis_output/factor_analysis_results.json")
print(f"🎯 最强因子: {summary_df.iloc[0]['factor']} (IC={summary_df.iloc[0]['ic']:.4f})")
