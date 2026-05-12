#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
使用调整后的参数测试
"""

import sys
sys.path.append('.')

from quarterly_scorer import load_stock_list, init_db, load_annual_from_db, calc_annual_score, fetch_quarterly_batch, calc_quarterly_score
from quarterly_scorer import Config
import random

def test_adjusted():
    print("=" * 80)
    print("使用调整后的参数测试")
    print("=" * 80)

    # 临时修改配置 - 降低A级门槛
    original_a = Config.GRADE_A
    Config.GRADE_A = 15.0  # 将A级门槛降到15分

    try:
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
        print("\n计算年报评分...")
        annual_scored = []
        a_stocks = []

        for i, s in enumerate(annual_data):
            score = calc_annual_score(s, industry_groups, all_stocks)
            annual_scored.append(score)
            if score.get("grade") == "A":
                a_stocks.append(score)

            if (i + 1) % 1000 == 0:
                print(f"已处理 {i + 1} 只股票...")

        print(f"\n年报A级股票总数: {len(a_stocks)} 只")

        if a_stocks:
            print("\n前10只年报A级股票:")
            print("-" * 100)
            for stock in sorted(a_stocks, key=lambda x: x["total_score"], reverse=True)[:10]:
                print(f"{stock['ts_code']} {stock['name']}: 评分={stock['total_score']}, "
                      f"ROE={stock['roe']}, 毛利率={stock['gross_margin']}, 净利率={stock['net_margin']}, "
                      f"营收同比={stock['revenue_yoy']}, 利润同比={stock['profit_yoy']}")

        # 获取季度数据（使用模拟数据）
        print("\n获取季度数据...")
        token = "dummy_token"
        quarterly_raw = fetch_quarterly_batch(annual_data, token, force_refresh=False, conn=conn)

        # 合并季度评分
        print("\n计算季度评分...")
        quarterly_scored = []
        q_a_stocks = []

        for a in annual_data:
            ts_code = a["ts_code"]
            q = next((r for r in quarterly_raw if r["ts_code"] == ts_code), None)
            if q and q.get("fetch_success"):
                score = calc_quarterly_score(a, q["metrics"], industry_groups, all_stocks)
                score["quarterly_total_score"] = score["total_score"]
                score["quarterly_grade"] = score["grade"]
                quarterly_scored.append(score)

                if score.get("quarterly_grade") == "A":
                    q_a_stocks.append(score)
            else:
                # 季度数据失败，复制年报评分但标记
                s = calc_annual_score(a, industry_groups, all_stocks)
                s["data_source"] = "年报（无季度）"
                s["quarterly_total_score"] = None
                s["quarterly_grade"] = None
                quarterly_scored.append(s)

        print(f"\n季报A级股票总数: {len(q_a_stocks)} 只")

        # 交集计算
        annual_a_codes = {r["ts_code"] for r in annual_scored if r.get("grade") == "A"}
        quarterly_a_codes = {r["ts_code"] for r in quarterly_scored if r.get("quarterly_grade") == "A"}
        preferred_codes = annual_a_codes & quarterly_a_codes

        print(f"\n★ 交集优选: {len(preferred_codes)} 只 ★")

        if preferred_codes:
            print("\n优选股票列表 (年报A∩季报A):")
            print("-" * 100)
            preferred_stocks = [r for r in quarterly_scored if r["ts_code"] in preferred_codes]
            for stock in sorted(preferred_stocks, key=lambda x: x["total_score"], reverse=True):
                print(f"{stock['ts_code']} {stock['name']}: "
                      f"年报评分={stock.get('total_score')}({stock.get('grade')}), "
                      f"季报评分={stock.get('quarterly_total_score')}({stock.get('quarterly_grade')})")

        # 随机验证一些股票
        sample_size = min(10, len(stocks))
        sample_codes = random.sample(list(stocks), sample_size)
        print(f"\n随机验证 {sample_size} 只股票:")
        print("-" * 80)

        for code in sample_codes:
            a = next((r for r in annual_scored if r["ts_code"] == code), None)
            q = next((r for r in quarterly_scored if r["ts_code"] == code), None)
            if a and q:
                print(f"{code}: 年报评分={a.get('total_score','N/A')}({a.get('grade','N/A')}), "
                      f"季报评分={q.get('quarterly_total_score','N/A')}({q.get('quarterly_grade','N/A')})")

    finally:
        # 恢复原始配置
        Config.GRADE_A = original_a

    conn.close()
    print("\n调整后验证完成！")

if __name__ == "__main__":
    test_adjusted()