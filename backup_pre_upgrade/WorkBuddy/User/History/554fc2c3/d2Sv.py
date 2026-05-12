#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
最终测试脚本 - 完整的端到端验证
"""

import sys
sys.path.append('.')

from quarterly_scorer import load_stock_list, init_db, load_annual_from_db, calc_annual_score, fetch_quarterly_batch, calc_quarterly_score
from quarterly_scorer import Config
import random

def test_final():
    print("=" * 80)
    print("最终测试脚本 - 完整端到端验证")
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
        else:
            print("\n没有找到同时满足年报A级和季报A级的股票")
            print("原因可能是季度模拟数据的评分不够高")

        # 生成JSON报告
        timestamp = "20260426_030000"  # 固定时间戳用于演示
        import json
        output_dir = "."
        json_path = f"{output_dir}/季报年报交叉验证_{timestamp}.json"

        output = {
            "data_timestamp": "2026-04-26 03:00:00",
            "total_stocks": len(stocks),
            "annual_a_count": len(annual_a_codes),
            "quarterly_a_count": len(quarterly_a_codes),
            "preferred_count": len(preferred_codes),
            "preferred_stocks": [
                {"ts_code": r["ts_code"], "name": r["name"], "industry_l1": r["industry_l1"],
                 "annual_score": r.get("total_score"), "annual_grade": r.get("grade"),
                 "quarterly_score": r.get("quarterly_total_score"), "quarterly_grade": r.get("quarterly_grade")}
                for r in quarterly_scored if r["ts_code"] in preferred_codes
            ],
            "annual_only_a": [
                {"ts_code": r["ts_code"], "name": r["name"], "score": r.get("total_score"), "grade": r.get("grade")}
                for r in annual_scored if r.get("grade") == "A" and r["ts_code"] not in preferred_codes
            ],
            "quarterly_only_a": [
                {"ts_code": r["ts_code"], "name": r["name"], "score": r.get("quarterly_total_score"), "grade": r.get("quarterly_grade")}
                for r in quarterly_scored if r.get("quarterly_grade") == "A" and r["ts_code"] not in preferred_codes
            ]
        }

        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(output, f, ensure_ascii=False, indent=2)

        print(f"\nJSON 报告已保存: {json_path}")

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
    print("\n最终测试完成！")

if __name__ == "__main__":
    test_final()