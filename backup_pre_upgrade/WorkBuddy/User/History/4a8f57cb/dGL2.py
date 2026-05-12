#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
查看最高评分的股票
"""

import sys
sys.path.append('.')

from quarterly_scorer import load_stock_list, init_db, load_annual_from_db, calc_annual_score
import random

def highest_score():
    print("=" * 80)
    print("查看最高评分的股票")
    print("=" * 80)

    # 加载股票列表
    stocks = load_stock_list()
    if not stocks:
        print("股票列表为空")
        return

    # 初始化数据库
    conn = init_db()

    # 加载年报数据
    annual_data = load_annual_from_db(conn, stocks)
    print(f"从缓存加载年报数据: {len(annual_data)} 只")

    # 按行业分组（用于评分）
    industry_groups = {}
    for s in annual_data:
        ind = s.get("industry_l1", "未知")
        if ind not in industry_groups:
            industry_groups[ind] = []
        industry_groups[ind].append(s)
    all_stocks = annual_data

    # 计算评分并排序
    scored = []
    for i, s in enumerate(annual_data):
        score = calc_annual_score(s, industry_groups, all_stocks)
        scored.append(score)

        if (i + 1) % 1000 == 0:
            print(f"已处理 {i + 1} 只股票...")

    # 按评分排序
    sorted_stocks = sorted(scored, key=lambda x: x["total_score"], reverse=True)

    print(f"\n评分最高的10只股票:")
    print("-" * 120)
    for i, stock in enumerate(sorted_stocks[:10]):
        print(f"{i+1}. {stock['ts_code']} {stock['name']}: "
              f"评分={stock['total_score']}({stock['grade']}), "
              f"ROE={stock['roe']}, 毛利率={stock['gross_margin']}, 净利率={stock['net_margin']}, "
              f"营收同比={stock['revenue_yoy']}, 利润同比={stock['profit_yoy']}, "
              f"现金流={stock['ocf_to_profit']}, 负债率={stock['debt_ratio']}")

    # 查看一些随机股票
    sample_codes = random.sample(list(stocks), min(5, len(stocks)))
    print(f"\n随机5只股票示例:")
    print("-" * 80)
    for code in sample_codes:
        stock = next((s for s in scored if s["ts_code"] == code), None)
        if stock:
            print(f"{code}: 评分={stock['total_score']}({stock['grade']})")

    conn.close()
    print("\n完成！")

if __name__ == "__main__":
    highest_score()