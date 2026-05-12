#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""步骤1：验证备用数据源字段准确性"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import subprocess

print("=" * 60)
print("调试 subprocess 输出")
print("=" * 60)

r = subprocess.run(
    'npx --yes westock-data-skillhub@latest profile sh600519',
    shell=True, capture_output=True, text=True, encoding='utf-8', timeout=60
)

print(f"returncode: {r.returncode}")
print(f"stdout len: {len(r.stdout)}")
print(f"stderr len: {len(r.stderr)}")

# 检查 stdout 中的表格行
print("\n--- stdout 表格行 ---")
for line in r.stdout.split('\n'):
    stripped = line.strip()
    if stripped.startswith('|'):
        print(f"  [{stripped[:80]}...]")

# 检查 stderr 中的表格行
print("\n--- stderr 表格行 ---")
for line in r.stderr.split('\n'):
    stripped = line.strip()
    if stripped.startswith('|'):
        print(f"  [{stripped[:80]}...]")

# 合并输出
output = r.stdout + r.stderr
print("\n--- 合并输出表格行 ---")
lines = [l.strip() for l in output.split('\n') if l.strip().startswith('|')]
print(f"  共 {len(lines)} 行")
for l in lines[:3]:
    print(f"  {l[:120]}")

# 模拟 _westock_profile 解析
if len(lines) >= 3:
    header = [c.strip() for c in lines[0].split('|')[1:-1]]
    values = [c.strip() for c in lines[1].split('|')[1:-1]]
    print(f"\n  header: {header}")
    print(f"  values: {values}")
    result = {}
    for h, v in zip(header, values):
        h_lower = h.lower()
        if 'name' in h_lower and 'code' not in h_lower:
            result['name'] = v
        elif 'industry' in h_lower:
            result['industry'] = v
    print(f"  parsed: {result}")
else:
    print(f"\n  行数不足3行，实际输出:")
    print(output[:500])
