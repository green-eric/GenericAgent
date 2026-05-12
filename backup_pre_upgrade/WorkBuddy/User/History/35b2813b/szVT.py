#!/usr/bin/env python3

# 简单测试脚本，验证核心功能
import os
import sys

print("开始测试...")

# 检查文件是否存在
if not os.path.exists('d:/Project/QAScorer/qa_scorer.py'):
    print("错误: qa_scorer.py 文件不存在")
    exit(1)

# 尝试读取文件
try:
    with open('d:/Project/QAScorer/qa_scorer.py', 'r', encoding='utf-8') as f:
        content = f.read()

    # 检查基本结构
    if 'def fetch_quarterly_data' in content:
        print("✓ 找到 fetch_quarterly_data 函数")
    else:
        print("✗ 未找到 fetch_quarterly_data 函数")

    if 'get_combined_financials' in content:
        print("✓ 找到 get_combined_financials 函数")
    else:
        print("✗ 未找到 get_combined_financials 函数")

    # 检查是否有语法错误
    try:
        compile(content, 'd:/Project/QAScorer/qa_scorer.py', 'exec')
        print("✓ 文件语法正确")
    except SyntaxError as e:
        print(f"✗ 语法错误: {e}")
        exit(1)

    print("测试完成！")

except Exception as e:
    print(f"错误: {e}")
    exit(1)