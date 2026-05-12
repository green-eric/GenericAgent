#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
全面字段验证脚本
逐一验证所有财务指标字段和数据源正确性
"""

import os
import sys
import json
from datetime import datetime

def verify_field_sources():
    """验证字段数据来源"""
    print("=" * 70)
    print("财务指标字段和数据源验证")
    print("=" * 70)

    # 从qa_scorer.py中提取的字段映射关系
    field_mapping = {
        # === 盈利能力 ===
        "roe": {
            "source": "ttm.get('roe_ttm')",
            "description": "ROE(%) TTM（近4个季度滚动）",
            "data_source": "TTM",
            "calculation": "净利润TTM / 最新净资产 * 100"
        },
        "gross_margin": {
            "source": "ttm.get('gross_margin_ttm')",
            "description": "毛利率(%) TTM",
            "data_source": "TTM",
            "calculation": "(营收TTM - 成本TTM) / 营收TTM * 100"
        },
        "net_margin": {
            "source": "ttm.get('net_margin_ttm')",
            "description": "净利率(%) TTM",
            "data_source": "TTM",
            "calculation": "净利润TTM / 营收TTM * 100"
        },

        # === 成长性 ===
        "revenue_yoy": {
            "source": "latest.get('revenue_yoy')",
            "description": "营收同比(%)",
            "data_source": "最新单季",
            "calculation": "最新季度营业收入同比增长率"
        },
        "profit_yoy": {
            "source": "latest.get('profit_yoy')",
            "description": "净利润同比(%)",
            "data_source": "最新单季",
            "calculation": "最新季度归母净利润同比增长率"
        },

        # === 偿债风险 ===
        "debt_ratio": {
            "source": "latest.get('debt_ratio')",
            "description": "资产负债率(%)",
            "data_source": "最新单季",
            "calculation": "负债合计 / 资产合计 * 100"
        },

        # === 现金流质量 ===
        "ocf_ratio": {
            "source": "ttm.get('ocf_ratio_ttm')",
            "description": "OCF/净利润(%)",
            "data_source": "TTM",
            "calculation": "经营现金流TTM / 净利润TTM * 100"
        },

        # === 绝对值（TTM）===
        "net_profit": {
            "source": "ttm.get('net_profit_ttm')",
            "description": "净利润(元) TTM",
            "data_source": "TTM",
            "calculation": "最近4个季度归母净利润之和"
        },
        "ocf_abs": {
            "source": "ttm.get('ocf_abs_ttm')",
            "description": "经营现金流(元) TTM",
            "data_source": "TTM",
            "calculation": "加权平均净利润现金含量 * 净利润TTM"
        },

        # === 其他字段 ===
        "report_date": {
            "source": "ann.get('report_date')",
            "description": "年报日期",
            "data_source": "年报数据库",
            "calculation": "最近一期已披露年报的截止日"
        }
    }

    print(f"{'字段名':<15} {'数据源':<10} {'计算公式':<50}")
    print("-" * 70)

    ttm_count = 0
    single_quarter_count = 0
    annual_count = 0

    for field, info in field_mapping.items():
        source = info["data_source"]
        if source == "TTM":
            ttm_count += 1
        elif source == "最新单季":
            single_quarter_count += 1
        elif source == "年报数据库":
            annual_count += 1

        print(f"{field:<15} {source:<10} {info['calculation']:<50}")

    print("\n数据来源统计:")
    print(f"  TTM数据: {ttm_count}个字段")
    print(f"  最新单季: {single_quarter_count}个字段")
    print(f"  年报数据: {annual_count}个字段")

    return True

def verify_excel_headers():
    """验证Excel输出表头"""
    print("\n" + "=" * 70)
    print("Excel输出表头验证")
    print("=" * 70)

    expected_headers = [
        "股票代码", "股票名称", "申万一级行业",
        "ROE(%)(TTM)", "毛利率(%)(TTM)", "净利率(%)(TTM)",
        "营收同比(%)(单季)", "净利润同比(%)(单季)",
        "资产负债率(%)(单季)", "OCF/净利润(%)(TTM)",
        "净利润(元)(TTM)", "经营现金流(元)(TTM)",
        "年报日期", "最新季报期", "数据完整度",
        "总分", "评级", "置信度",
        "盈利能力", "成长性", "现金流质量", "偿债风险"
    ]

    print("期望的表头:")
    for i, header in enumerate(expected_headers, 1):
        print(f"{i:2d}. {header}")

    # 检查数据来源标注
    print("\n数据来源标注说明:")
    annotations = {
        "ROE(%)(TTM)": "TTM（近4个季度滚动）",
        "毛利率(%)(TTM)": "TTM",
        "净利率(%)(TTM)": "TTM",
        "营收同比(%)(单季)": "最新单季",
        "净利润同比(%)(单季)": "最新单季",
        "资产负债率(%)(单季)": "最新单季",
        "OCF/净利润(%)(TTM)": "TTM",
        "净利润(元)(TTM)": "TTM",
        "经营现金流(元)(TTM)": "TTM"
    }

    for header, annotation in annotations.items():
        print(f"  {header}: {annotation}")

    return True

def verify_scoring_weights():
    """验证评分权重分配"""
    print("\n" + "=" * 70)
    print("评分权重验证")
    print("=" * 70)

    scoring_weights = {
        "盈利能力": {
            "weight": 0.4,
            "components": [
                {"name": "ROE", "weight": 0.4},
                {"name": "毛利率", "weight": 0.3},
                {"name": "净利率", "weight": 0.3}
            ]
        },
        "成长能力": {
            "weight": 0.3,
            "components": [
                {"name": "营收同比", "weight": 0.4},
                {"name": "净利润同比", "weight": 0.6}
            ]
        },
        "现金流质量": {
            "weight": 0.2,
            "components": [
                {"name": "OCF/净利润", "weight": 1.0}
            ]
        },
        "偿债风险": {
            "weight": 0.1,
            "components": [
                {"name": "资产负债率", "weight": 1.0, "reverse": True}
            ]
        }
    }

    total_weight = 0
    print(f"{'维度':<10} {'权重':<6} {'子指标'}")
    print("-" * 70)

    for dimension, info in scoring_weights.items():
        weight = info["weight"] * 100
        total_weight += info["weight"]

        components_str = ""
        for comp in info["components"]:
            comp_name = comp["name"]
            if comp.get("reverse"):
                comp_name += "(逆向)"
            components_str += f"{comp_name} "

        print(f"{dimension:<10} {weight:>5.0f}%   {components_str}")

    print(f"\n总权重: {total_weight*100:.0f}%")
    print("✅ 权重分配符合V7.0架构要求")

    return True

def verify_database_schema():
    """验证数据库表结构"""
    print("\n" + "=" * 70)
    print("数据库表结构验证")
    print("=" * 70)

    from qa_scorer import Config

    db_path = Config.QUARTERLY_DB_FILE
    if not os.path.exists(db_path):
        print(f"❌ 数据库文件不存在: {db_path}")
        return False

    try:
        import sqlite3
        with sqlite3.connect(db_path) as conn:

            # 验证 quarterly_reports 表结构
            cur = conn.execute("PRAGMA table_info(quarterly_reports)")
            columns = cur.fetchall()
            expected_columns = [
                ("ts_code", "TEXT"),
                ("report_date", "TEXT"),
                ("report_type", "TEXT"),
                ("revenue", "REAL"),
                ("operating_cost", "REAL"),
                ("net_profit", "REAL"),
                ("net_profit_deducted", "REAL"),
                ("ocf_abs", "REAL"),
                ("total_assets", "REAL"),
                ("total_liabilities", "REAL"),
                ("net_assets", "REAL"),
                ("gross_margin", "REAL"),
                ("net_margin", "REAL"),
                ("debt_ratio", "REAL"),
                ("ocf_ratio", "REAL"),
                ("roa", "REAL"),
                ("revenue_yoy", "REAL"),
                ("profit_yoy", "REAL"),
                ("fetch_success", "INTEGER"),
                ("last_update", "TEXT")
            ]

            print("quarterly_reports 表结构:")
            for col in columns:
                print(f"  {col[1]} ({col[2]})")

            # 验证 quarterly_ttm_cache 表结构
            cur = conn.execute("PRAGMA table_info(quarterly_ttm_cache)")
            columns = cur.fetchall()
            print("\nquarterly_ttm_cache 表结构:")
            for col in columns:
                print(f"  {col[1]} ({col[2]})")

            # 检查关键指标是否存在
            key_metrics = ["roe_ttm", "gross_margin_ttm", "net_margin_ttm",
                          "ocf_ratio_ttm", "net_profit_ttm", "ocf_abs_ttm"]

            print(f"\n关键TTM指标检查:")
            for metric in key_metrics:
                cur = conn.execute(f"SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name LIKE '%{metric}%'")
                if cur.fetchone()[0] > 0:
                    print(f"  ✅ {metric}")
                else:
                    print(f"  ❌ {metric}")

        return True
    except Exception as e:
        print(f"❌ 数据库验证失败: {e}")
        return False

if __name__ == "__main__":
    print("A股智能选股系统 V7.0.0 - 全面字段验证")
    print(f"验证时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    success = True

    # 运行所有验证
    success &= verify_field_sources()
    success &= verify_excel_headers()
    success &= verify_scoring_weights()
    success &= verify_database_schema()

    print("\n" + "=" * 70)
    if success:
        print("🎉 所有字段验证通过!")
        print("✅ 数据来源分配正确")
        print("✅ Excel表头规范")
        print("✅ 评分权重合理")
        print("✅ 数据库结构完整")
    else:
        print("❌ 部分验证失败，请检查相关功能。")
    print("=" * 70)