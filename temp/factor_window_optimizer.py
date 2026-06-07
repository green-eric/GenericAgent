#!/usr/bin/env python3
"""
因子窗口选择原型 — 基于stock_data.db只读查询
================================================
目标: 对不同因子测试不同回看窗口(5d/10d/20d/60d)，找到各因子的最优窗口
数据: quotes_ic表(245万行, 2024-01~2026-05), quotes表(321万行, 2023-02~2026-05)

方法:
  1. 计算各因子在不同窗口下的IC(IC=因子排名与未来收益排名的Spearman相关系数)
  2. 找最优窗口
  3. 对比"统一窗口"vs"最优窗口"的IC提升

⚠️ 只读操作，不修改D:\Project
"""

import sqlite3
import numpy as np
from scipy import stats
from collections import defaultdict
import json
from datetime import datetime, timedelta

DB_PATH = r"D:\GenericAgent\temp\data\stock_data.db"

# ─── 因子定义 ───────────────────────────────────────────
# quotes_ic表中可用因子: ma_5, ma_10, ma_20, ret_5d, ret_10d, ret_1m, mom_3m, industry_mom_1m, industry_mom_3m
# 衍生因子: 价格相对MA(close/ma - 1), 短期动量(ret_5d), 中期动量(ret_1m)

WINDOWS = [5, 10, 20, 60]  # 回看窗口(交易日)

def load_data(conn, start_date="2024-03-01", end_date="2026-04-30"):
    """加载quotes_ic数据"""
    query = """
    SELECT symbol, trade_date, close_price,
           ma_5, ma_10, ma_20,
           ret_5d, ret_10d, ret_1m, mom_3m,
           industry_mom_1m, industry_mom_3m,
           fwd_ret
    FROM quotes_ic
    WHERE trade_date BETWEEN ? AND ?
      AND fwd_ret IS NOT NULL
      AND close_price IS NOT NULL
    ORDER BY trade_date, symbol
    """
    cursor = conn.execute(query, (start_date, end_date))
    rows = cursor.fetchall()
    cols = [d[0] for d in cursor.description]
    return cols, rows


def compute_factor_values(rows, cols):
    """计算衍生因子"""
    data = []
    for row in rows:
        d = dict(zip(cols, row))
        close = d['close_price']
        
        # 跳过无效数据
        if close is None or close <= 0:
            continue
        
        d['price_vs_ma5'] = (close / d['ma_5'] - 1) if d['ma_5'] and d['ma_5'] > 0 else None
        d['price_vs_ma10'] = (close / d['ma_10'] - 1) if d['ma_10'] and d['ma_10'] > 0 else None
        d['price_vs_ma20'] = (close / d['ma_20'] - 1) if d['ma_20'] and d['ma_20'] > 0 else None
        d['ma5_vs_ma20'] = (d['ma_5'] / d['ma_20'] - 1) if d['ma_20'] and d['ma_20'] > 0 else None
        d['short_mom'] = d['ret_5d']  # 短期动量
        d['mid_mom'] = d['ret_1m']    # 中期动量
        d['ind_mom'] = d['industry_mom_1m']  # 行业动量
        
        data.append(d)
    return data


def compute_ic_by_window(data, factor_name, window_days, date_index):
    """
    对给定因子和窗口，计算每日IC
    date_index: {date: [records]} 分组
    返回: IC时间序列
    """
    ic_series = []
    
    dates = sorted(date_index.keys())
    for i in range(window_days, len(dates)):
        date = dates[i]
        
        # 收集过去window_days的因子值和fwd_ret
        factor_vals = []
        fwd_rets = []
        
        # 当天有数据的股票
        for rec in date_index[date]:
            fv = rec.get(factor_name)
            fr = rec.get('fwd_ret')
            if fv is not None and fr is not None:
                factor_vals.append(fv)
                fwd_rets.append(fr)
        
        if len(factor_vals) < 30:  # 至少30只股票
            continue
        
        # Spearman秩相关
        try:
            corr, pval = stats.spearmanr(factor_vals, fwd_rets)
            if not np.isnan(corr):
                ic_series.append({
                    'date': date,
                    'ic': corr,
                    'pval': pval,
                    'n_stocks': len(factor_vals)
                })
        except:
            continue
    
    return ic_series


def analyze_all_factors(conn):
    """主分析"""
    print("=" * 60)
    print("因子窗口选择原型分析")
    print("=" * 60)
    
    # 1. 加载数据
    print("\n[1/4] 加载数据...")
    cols, rows = load_data(conn)
    print(f"  原始行数: {len(rows):,}")
    
    # 2. 计算衍生因子
    print("[2/4] 计算衍生因子...")
    data = compute_factor_values(rows, cols)
    print(f"  有效行数: {len(data):,}")
    
    # 按日期分组
    date_index = defaultdict(list)
    for rec in data:
        date_index[rec['trade_date']].append(rec)
    print(f"  交易日数: {len(date_index)}")
    
    # 3. 对每个因子×每个窗口计算IC
    print("[3/4] 计算IC矩阵...")
    
    factor_names = [
        'price_vs_ma5', 'price_vs_ma10', 'price_vs_ma20', 'ma5_vs_ma20',
        'short_mom', 'mid_mom', 'ind_mom',
        'industry_mom_1m', 'industry_mom_3m'
    ]
    
    results = {}
    
    for factor in factor_names:
        results[factor] = {}
        for window in WINDOWS:
            ic_series = compute_ic_by_window(data, factor, window, date_index)
            
            if len(ic_series) > 10:
                ics = [x['ic'] for x in ic_series]
                ic_mean = np.mean(ics)
                ic_std = np.std(ics)
                ic_ir = ic_mean / ic_std if ic_std > 0 else 0
                pvals = [x['pval'] for x in ic_series]
                sig_rate = np.mean([p < 0.05 for p in pvals])
                
                results[factor][window] = {
                    'ic_mean': round(ic_mean, 4),
                    'ic_std': round(ic_std, 4),
                    'ic_ir': round(ic_ir, 4),
                    'sig_rate': round(sig_rate, 4),
                    'n_days': len(ic_series),
                    'n_stocks_avg': round(np.mean([x['n_stocks'] for x in ic_series]), 0)
                }
    
    # 4. 输出结果
    print("[4/4] 分析结果\n")
    
    # IC矩阵表
    print("=" * 80)
    print(f"{'因子':<20} | {'5d IC':>10} {'IR':>8} {'显著%':>8} | {'10d IC':>10} {'IR':>8} {'显著%':>8} | {'20d IC':>10} {'IR':>8} {'显著%':>8} | {'60d IC':>10} {'IR':>8} {'显著%':>8}")
    print("-" * 80)
    
    for factor in factor_names:
        parts = []
        for w in WINDOWS:
            r = results[factor].get(w)
            if r:
                parts.append(f"{r['ic_mean']:>10.4f} {r['ic_ir']:>8.3f} {r['sig_rate']:>8.1%}")
            else:
                parts.append(f"{'N/A':>10} {'N/A':>8} {'N/A':>8}")
        print(f"{factor:<20} | {' | '.join(parts)}")
    
    # 最优窗口
    print("\n" + "=" * 60)
    print("最优窗口推荐")
    print("=" * 60)
    
    for factor in factor_names:
        if not results[factor]:
            continue
        best_window = max(results[factor].keys(), key=lambda w: abs(results[factor][w]['ic_mean']))
        best = results[factor][best_window]
        print(f"  {factor:<20} → {best_window:>3d}d | IC={best['ic_mean']:>+.4f} IR={best['ic_ir']:.3f} 显著率={best['sig_rate']:.1%}")
    
    # 5. 统一窗口 vs 最优窗口对比
    print("\n" + "=" * 60)
    print("统一窗口(20d) vs 最优窗口 对比")
    print("=" * 60)
    
    improvement_count = 0
    for factor in factor_names:
        if not results[factor] or 20 not in results[factor]:
            continue
        uniform = results[factor][20]
        best_w = max(results[factor].keys(), key=lambda w: abs(results[factor][w]['ic_mean']))
        best = results[factor][best_w]
        diff = abs(best['ic_mean']) - abs(uniform['ic_mean'])
        if diff > 0:
            improvement_count += 1
        print(f"  {factor:<20}: 统一={uniform['ic_mean']:>+.4f} → 最优({best_w}d)={best['ic_mean']:>+.4f} | 提升={diff:>+.4f}")
    
    print(f"\n  最优窗口优于统一窗口: {improvement_count}/{len(factor_names)} 个因子")
    
    # 保存结果
    output = {
        'analysis_date': datetime.now().isoformat(),
        'data_range': '2024-01-02 ~ 2026-05-15',
        'n_stocks_days': len(data),
        'n_trading_days': len(date_index),
        'ic_matrix': {f: {str(w): r for w, r in wd.items()} for f, wd in results.items()},
        'best_windows': {}
    }
    
    for factor in factor_names:
        if results[factor]:
            best_w = max(results[factor].keys(), key=lambda w: abs(results[factor][w]['ic_mean']))
            output['best_windows'][factor] = {
                'window_days': best_w,
                **results[factor][best_w]
            }
    
    with open('autonomous_reports/factor_window_results.json', 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    
    print(f"\n结果已保存: autonomous_reports/factor_window_results.json")
    return output


if __name__ == "__main__":
    conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    try:
        analyze_all_factors(conn)
    finally:
        conn.close()
