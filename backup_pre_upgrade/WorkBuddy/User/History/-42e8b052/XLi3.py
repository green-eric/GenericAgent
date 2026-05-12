#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""检查westock-data是否能获取总市值和PE"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ['PYTHONIOENCODING'] = 'utf-8'

import subprocess
import io

# 修复Windows控制台编码
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

def run_westock(args):
    r = subprocess.run(
        f'npx --yes westock-data-skillhub@latest {args}',
        shell=True, capture_output=True, text=True, encoding='utf-8', timeout=60
    )
    output = r.stdout + r.stderr
    lines = [l.strip() for l in output.split('\n') if l.strip().startswith('|')]
    return lines

# 检查search返回的字段
print("=== search 600519 ===")
lines = run_westock("search 600519")
print(f"  表格行数: {len(lines)}")
for l in lines[:3]:
    print(f"  {l[:200]}")

# 检查kline返回的所有字段
print("\n=== kline sh600519 day 1 ===")
lines = run_westock("kline sh600519 day 1")
if lines:
    header = [c.strip() for c in lines[0].split('|')[1:-1]]
    print(f"  字段: {header}")
    if len(lines) >= 3:
        values = [c.strip() for c in lines[2].split('|')[1:-1]]
        for h, v in zip(header, values):
            print(f"    {h}: {v}")

# 检查finance返回的所有字段
print("\n=== finance sh600519 1 ===")
lines = run_westock("finance sh600519 1")
if lines:
    header = [c.strip() for c in lines[0].split('|')[1:-1]]
    print(f"  字段数: {len(header)}")
    for i, h in enumerate(header):
        print(f"    [{i}] {h}")

# 检查profile的所有字段
print("\n=== profile sh600519 ===")
lines = run_westock("profile sh600519")
if lines:
    header = [c.strip() for c in lines[0].split('|')[1:-1]]
    print(f"  字段数: {len(header)}")
    for i, h in enumerate(header):
        print(f"    [{i}] {h}")
    if len(lines) >= 3:
        values = [c.strip() for c in lines[2].split('|')[1:-1]]
        print(f"  值:")
        for h, v in zip(header, values):
            print(f"    {h}: {v}")
