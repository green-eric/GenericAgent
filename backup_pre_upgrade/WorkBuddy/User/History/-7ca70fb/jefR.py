#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
检查数据库实际内容
"""

import os
import sqlite3
from qa_scorer import Config

def check_ttm_cache_content():
    """检查TTM缓存表的内容"""
    print("=" * 60)
    print("TTM缓存表内容检查")
    print("=" * 60)

    db_path = Config.QUARTERLY_DB_FILE
    if not os.path.exists(db_path):
        print(f"❌ 数据库文件不存在: {db_path}")
        return

    try:
        with sqlite3.connect(db_path) as conn:
            # 检查表是否存在
            cur = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='quarterly_ttm_cache'")
            table_exists = cur.fetchone()

            if not table_exists:
                print("❌ quarterly_ttm_cache 表不存在")
                return

            print("✅ quarterly_ttm_cache 表存在")

            # 检查表中的列
            cur = conn.execute("PRAGMA table_info(quarterly_ttm_cache)")
            columns = cur.fetchall()
            print(f"\n表结构 ({len(columns)}列):")
            for col in columns:
                print(f"  {col[1]} ({col[2]})")

            # 检查数据行数
            cur = conn.execute("SELECT COUNT(*) FROM quarterly_ttm_cache")
            row_count = cur.fetchone()[0]
            print(f"\n数据行数: {row_count}")

            # 检查关键指标字段是否有数据
            key_columns = ["roe_ttm", "gross_margin_ttm", "net_margin_ttm",
                          "ocf_ratio_ttm", "net_profit_ttm", "ocf_abs_ttm"]

            print("\n关键指标数据检查:")
            for col in key_columns:
                if any(c[1] == col for c in columns):
                    cur = conn.execute(f"SELECT COUNT(*) FROM quarterly_ttm_cache WHERE {col} IS NOT NULL")
                    count = cur.fetchone()[0]
                    total = row_count
                    print(f"  {col}: {count}/{total} ({(count/total*100):.1f}%)")
                else:
                    print(f"  {col}: ❌ 字段不存在")

            # 显示一些样本数据
            print(f"\n样本数据 (前5条):")
            cur = conn.execute("""
                SELECT ts_code, roe_ttm, gross_margin_ttm, net_margin_ttm,
                       ocf_ratio_ttm, net_profit_ttm, ocf_abs_ttm
                FROM quarterly_ttm_cache
                LIMIT 5
            """)
            samples = cur.fetchall()
            for sample in samples:
                print(f"  {sample[0]}: ROE={sample[1]}, GM={sample[2]}, NM={sample[3]}, OCF={sample[4]}")

    except Exception as e:
        print(f"❌ 数据库检查失败: {e}")

if __name__ == "__main__":
    check_ttm_cache_content()