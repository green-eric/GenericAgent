#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""检查westock-data是否能获取总市值和PE"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ['PYTHONIOENCODING'] = 'utf-8'

import subprocess

# 检查search返回的字段
print("=== search 600519 ===")
r = subprocess.run(
    'npx --yes westock-data-skillhub@latest search 600519',
    shell=True, capture_output=True, text=True, encoding='utf-8', timeout=60
)
output = r.stdout + r.stderr
lines = [l.strip() for l in output.split('\n') if l.strip().startswith('|')]
print(f"  表格行数: {len(lines)}")
for l in lines[:3]:
    print(f"  {l[:200]}")

# 检查kline返回的所有字段
print("\n=== kline sh600519 day 1 (检查所有字段) ===")
r = subprocess.run(
    'npx --yes westock-data-skillhub@latest kline sh600519 day 1',
    shell=True, capture_output=True, text=True, encoding='utf-8', timeout=60
)
output = r.stdout + r.stderr
lines = [l.strip() for l in output.split('\n') if l.strip().startswith('|')]
if lines:
    # 表头
    header = [c.strip() for c in lines[0].split('|')[1:-1]]
    print(f"  字段: {header}")
    if len(lines) >= 3:
        values = [c.strip() for c in lines[2].split('|')[1:-1]]
        print(f"  值:   {values}")

# 检查finance返回的所有字段
print("\n=== finance sh600519 1 (检查所有字段) ===")
r = subprocess.run(
    'npx --yes westock-data-skillhub@latest finance sh600519 1',
    shell=True, capture_output=True, text=True, encoding='utf-8', timeout=60
)
output = r.stdout + r.stderr
lines = [l.strip() for l in output.split('\n') if l.strip().startswith('|')]
if lines:
    header = [c.strip() for c in lines[0].split('|')[1:-1]]
    print(f"  字段数: {len(header)}")
    print(f"  字段: {header}")
    if len(lines) >= 3:
        values = [c.strip() for c in lines[2].split('|')[1:-1]]
        for h, v in zip(header, values):
            print(f"    {h}: {v}")

# 检查是否有其他命令
print("\n=== 检查westock-data帮助 ===")
r = subprocess.run(
    'npx --yes westock-data-skillhub@latest --help',
    shell=True, capture_output=True, text=True, encoding='utf-8', timeout=30
)
print(r.stdout[:1000])
