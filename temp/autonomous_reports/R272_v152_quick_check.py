#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
R272: ScoreSys V15.2 回测快速验证
目标：验证V15.2权重优化器（负IC反向+绝对值归一化）vs 固定权重的IC表现
方法：直接调用weight_optimizer.compute_weights生成V15.2权重，
      与config.yaml中的固定权重对比，输出权重差异和IC预期改善
"""
import sys, os, json, logging
sys.path.insert(0, r'D:\Project\ScoreSys')

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger("R272")

from weight_optimizer import compute_weights, load_ic_data
from config import WEIGHTS, get_active_weights, MODE

def main():
    print("=" * 70)
    print("  ScoreSys V15.2 回测快速验证")
    print("=" * 70)
    
    # 1. 加载IC数据
    ic_data = load_ic_data()
    regimes = list(ic_data.keys())
    all_factors = set()
    for r in regimes:
        all_factors.update(ic_data[r].keys())
    all_factors = sorted(all_factors)
    print(f"\n📊 IC数据: {len(regimes)}个regime × {len(all_factors)}个因子")
    print(f"  Regimes: {', '.join(regimes)}")
    
    # 2. 对比每个regime下的V15.2权重 vs 固定权重
    print(f"\n{'=' * 70}")
    print(f"  Regime权重对比 (V15.2动态 vs 固定权重)")
    print(f"{'=' * 70}")
    
    # 固定权重（config.yaml中的weights）
    fixed_weights = WEIGHTS.copy()
    print(f"\n📌 固定权重 ({len(fixed_weights)}个因子):")
    for f, w in sorted(fixed_weights.items(), key=lambda x: -abs(x[1])):
        if w != 0:
            print(f"  {f:30s}: {w:+.4f}")
    
    # 对每个regime计算V15.2权重
    print(f"\n📌 V15.2动态权重 (按regime):")
    v152_weights_by_regime = {}
    
    for regime in regimes:
        ic = ic_data[regime]
        # 过滤非数值
        ic_clean = {k: v for k, v in ic.items() if isinstance(v, (int, float))}
        w = compute_weights(ic_clean)
        v152_weights_by_regime[regime] = w
        
        print(f"\n  [{regime}]")
        # 找负IC因子
        neg_factors = {k: v for k, v in ic_clean.items() if v < 0}
        if neg_factors:
            print(f"    ⚠️  负IC因子: {', '.join(f'{k}({v:.4f})' for k, v in neg_factors.items())}")
        
        # 显示权重（按绝对值排序）
        for f, wt in sorted(w.items(), key=lambda x: -abs(x[1])):
            marker = " ←负IC反向" if f in neg_factors and wt < 0 else ""
            if abs(wt) > 0.001:
                print(f"    {f:30s}: {wt:+.4f}{marker}")
    
    # 3. IC分析：V15.2预期改善
    print(f"\n{'=' * 70}")
    print(f"  IC分析: V15.2预期改善")
    print(f"{'=' * 70}")
    
    print(f"\n  Regime          | 固定权重IC | V15.2权重IC | 改善")
    print(f"  {'-' * 55}")
    
    total_fixed_ic = 0
    total_v152_ic = 0
    improved = 0
    
    for regime in regimes:
        ic = ic_data[regime]
        ic_clean = {k: v for k, v in ic.items() if isinstance(v, (int, float))}
        
        # 固定权重IC = sum(weight * IC)
        fixed_ic = sum(fixed_weights.get(f, 0) * ic_clean.get(f, 0) for f in all_factors)
        
        # V15.2权重IC
        w152 = v152_weights_by_regime[regime]
        v152_ic = sum(w152.get(f, 0) * ic_clean.get(f, 0) for f in all_factors)
        
        delta = v152_ic - fixed_ic
        marker = "✅" if delta > 0 else ("❌" if delta < 0 else "➖")
        
        print(f"  {regime:16s} | {fixed_ic:+.6f} | {v152_ic:+.6f} | {delta:+.6f} {marker}")
        
        total_fixed_ic += fixed_ic
        total_v152_ic += v152_ic
        if delta > 0:
            improved += 1
    
    avg_fixed = total_fixed_ic / len(regimes)
    avg_v152 = total_v152_ic / len(regimes)
    avg_delta = avg_v152 - avg_fixed
    
    print(f"  {'-' * 55}")
    print(f"  {'平均':16s} | {avg_fixed:+.6f} | {avg_v152:+.6f} | {avg_delta:+.6f}")
    print(f"\n  ✅ 改善: {improved}/{len(regimes)}个regime")
    
    # 4. 关键发现
    print(f"\n{'=' * 70}")
    print(f"  关键发现")
    print(f"{'=' * 70}")
    
    if avg_delta > 0:
        print(f"\n  ✅ V15.2权重平均IC改善: {avg_delta:+.6f}")
        print(f"     负IC因子方向反转+绝对值归一化策略有效")
    else:
        print(f"\n  ❌ V15.2权重平均IC未改善: {avg_delta:+.6f}")
        print(f"     需要进一步调查")
    
    # 检查是否有负IC因子被正确反转
    reversed_count = 0
    for regime in regimes:
        ic = ic_data[regime]
        ic_clean = {k: v for k, v in ic.items() if isinstance(v, (int, float))}
        w = v152_weights_by_regime[regime]
        for f, ic_val in ic_clean.items():
            if ic_val < 0 and w.get(f, 0) < 0:
                reversed_count += 1
    
    print(f"  📊 负IC因子被反转的(regime,因子)对: {reversed_count}")
    
    print(f"\n{'=' * 70}")
    print(f"  结论: V15.2权重优化器验证完成")
    print(f"{'=' * 70}")
    print(f"  ⚠️  注意: 这是权重层面的IC分析，非完整回测")
    print(f"  完整回测需运行: python backtest.py --mode ic --start 2024-01-01 --end 2025-12-31")
    print(f"  建议在backtest.py中增加--compare-mode参数来对比V15.1 vs V15.2")

if __name__ == '__main__':
    main()
