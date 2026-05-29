#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
R273 — ScoreSys min_score参数扫描
扫描 min_score=[20,30,40,50,60,70] 对回测结果的影响
使用 run_backtest + 2024-2025年数据
"""
import sys, os, json, time
from datetime import datetime

sys.path.insert(0, r'D:\Project\ScoreSys')
from backtest import BacktestEngine

def main():
    db_path = r'D:\Project\ScoreSys\data\stock_data.duckdb'
    start_date = '2024-01-01'
    end_date = '2025-06-30'
    top_n = 20
    rebalance_months = 3
    min_scores = [20, 30, 40, 50, 60, 70]

    print("=" * 70)
    print("  R273 — ScoreSys min_score参数扫描")
    print("=" * 70)
    print(f"区间: {start_date} ~ {end_date} | top_n={top_n} | rebalance={rebalance_months}m")
    print(f"min_score候选: {min_scores}\n")

    engine = BacktestEngine(db_path=db_path)
    results = []

    for ms in min_scores:
        print(f"--- min_score={ms} ---", flush=True)
        t0 = time.time()
        try:
            r = engine.run_backtest(
                start_date=start_date,
                end_date=end_date,
                top_n=top_n,
                min_score=ms,
                rebalance_months=rebalance_months,
                equal_weight=True,
            )
            elapsed = time.time() - t0
            metrics = {
                'min_score': ms,
                'total_return': r.get('total_return', 0),
                'annual_return': r.get('annual_return', 0),
                'sharpe': r.get('sharpe_ratio', 0),
                'max_drawdown': r.get('max_drawdown', 0),
                'win_rate': r.get('win_rate', 0),
                'n_periods': r.get('n_periods', 0),
                'final_value': r.get('final_value', 0),
                'avg_period_return': r.get('avg_period_return', 0),
                'elapsed_sec': round(elapsed, 1),
            }
            results.append(metrics)
            print(f"  年化={metrics['annual_return']:.2%} 夏普={metrics['sharpe']:.3f} "
                  f"回撤={metrics['max_drawdown']:.2%} 胜率={metrics['win_rate']:.1%} "
                  f"期数={metrics['n_periods']} 耗时={elapsed:.1f}s\n")
        except Exception as e:
            print(f"  ERROR: {e}\n")
            results.append({'min_score': ms, 'error': str(e)})

    # 汇总
    valid = [r for r in results if 'error' not in r]
    if valid:
        print("=" * 70)
        print(f"{'min_score':>10} | {'年化收益':>8} | {'夏普':>6} | {'最大回撤':>8} | {'胜率':>6} | {'期数':>4}")
        print("-" * 60)
        for r in valid:
            print(f"{r['min_score']:>10} | {r['annual_return']:>7.2%} | {r['sharpe']:>5.3f} | "
                  f"{r['max_drawdown']:>7.2%} | {r['win_rate']:>5.1%} | {r['n_periods']:>4}")

        best_sharpe = max(valid, key=lambda x: x['sharpe'])
        best_return = max(valid, key=lambda x: x['annual_return'])
        print(f"\n最优夏普: min_score={best_sharpe['min_score']} → {best_sharpe['sharpe']:.3f}")
        print(f"最优收益: min_score={best_return['min_score']} → {best_return['annual_return']:.2%}")

    # 保存JSON
    output = {
        'timestamp': datetime.now().isoformat(),
        'params': {'start': start_date, 'end': end_date, 'top_n': top_n, 'rebalance_months': rebalance_months},
        'results': results,
    }
    out_path = r'D:\GenericAgent\temp\autonomous_reports\R273_min_score_sweep.json'
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"\n结果已保存: {out_path}")
    return results

if __name__ == '__main__':
    main()
