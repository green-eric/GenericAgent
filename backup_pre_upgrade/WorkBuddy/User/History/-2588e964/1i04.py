#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简单验证脚本
"""

import sys
sys.path.append('.')

from quarterly_scorer import main, load_stock_list, init_db, load_annual_from_db, calc_annual_score, fetch_quarterly_batch, calc_quarterly_score
import random

def test_verify():
    print("=" * 60)
    print("开始随机验证10只股票...")
    print("=" * 60)

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

    # 计算年报评分
    print("计算年报评分...")
    annual_scored = []
    for s in annual_data:
        score = calc_annual_score(s, industry_groups, all_stocks)
        annual_scored.append(score)

    # 获取季度数据（使用模拟数据）
    print("获取季度数据...")
    token = "dummy_token"
    quarterly_raw = fetch_quarterly_batch(annual_data, token, force_refresh=False, conn=conn)

    # 合并季度评分
    print("计算季度评分...")
    quarterly_scored = []
    for a in annual_data:
        ts_code = a["ts_code"]
        q = next((r for r in quarterly_raw if r["ts_code"] == ts_code), None)
        if q and q.get("fetch_success"):
            score = calc_quarterly_score(a, q["metrics"], industry_groups, all_stocks)
            score["quarterly_total_score"] = score["total_score"]
            score["quarterly_grade"] = score["grade"]
            quarterly_scored.append(score)
        else:
            # 季度数据失败，复制年报评分但标记
            s = calc_annual_score(a, industry_groups, all_stocks)
            s["data_source"] = "年报（无季度）"
            s["quarterly_total_score"] = None
            s["quarterly_grade"] = None
            quarterly_scored.append(s)

    # 随机验证10只股票
    sample_codes = random.sample(list(stocks), min(10, len(stocks)))
    print(f"\n随机验证 {len(sample_codes)} 只股票:")
    print("-" * 80)

    for code in sample_codes:
        a = next((r for r in annual_scored if r["ts_code"] == code), None)
        q = next((r for r in quarterly_scored if r["ts_code"] == code), None)
        if a and q:
            print(f"{code}: 年报评分={a.get('total_score','N/A')}({a.get('grade','N/A')}), "
                  f"季报评分={q.get('quarterly_total_score','N/A')}({q.get('quarterly_grade','N/A')})")

    # 交集计算
    annual_a_codes = {r["ts_code"] for r in annual_scored if r.get("grade") == "A"}
    quarterly_a_codes = {r["ts_code"] for r in quarterly_scored if r.get("quarterly_grade") == "A"}
    preferred_codes = annual_a_codes & quarterly_a_codes

    print(f"\n统计结果:")
    print(f"年报A级: {len(annual_a_codes)} 只")
    print(f"季报A级: {len(quarterly_a_codes)} 只")
    print(f"★ 交集优选: {len(preferred_codes)} 只 ★")

    conn.close()
    print("\n验证完成！")

if __name__ == "__main__":
    test_verify()