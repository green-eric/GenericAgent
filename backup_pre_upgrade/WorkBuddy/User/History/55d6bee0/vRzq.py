#!/usr/bin/env python3
"""
简单检查输出字段
"""

import json
import openpyxl

print("=== 字段检查 ===")

# 检查JSON文件
with open('季报年报交叉验证_20260426_092933.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

print("JSON字段:")
print("- data_timestamp:", "data_timestamp" in data)
print("- total_stocks:", "total_stocks" in data)
print("- annual_a_count:", "annual_a_count" in data)
print("- quarterly_a_count:", "quarterly_a_count" in data)
print("- preferred_count:", "preferred_count" in data)
print("- preferred_stocks:", len(data.get('preferred_stocks', [])), "items")
print("- annual_only_a:", len(data.get('annual_only_a', [])), "items")
print("- quarterly_only_a:", len(data.get('quarterly_only_a', [])), "items")

# 检查Excel文件
try:
    wb = openpyxl.load_workbook('季度评分_20260426_092933.xlsx')
    print("\nExcel工作表:", wb.sheetnames)
    wb.close()
except Exception as e:
    print(f"\nExcel错误: {e}")

print("\n检查完成")