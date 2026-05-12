#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""检查westock-data返回字段，确保与data_provider.py中的使用方式匹配"""
import subprocess, json, sys

def run_westock(args):
    cmd = f"npx --yes westock-data-skillhub@latest {args}"
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True, encoding='utf-8', timeout=60)
    return r.stdout + r.stderr

# 测试profile
print("=== profile sh600519 ===")
out = run_westock("profile sh600519")
# 找到表格部分
lines = [l for l in out.split('\n') if l.startswith('|')]
for l in lines[:3]:
    print(l)

print("\n=== profile sz000858 ===")
out = run_westock("profile sz000858")
lines = [l for l in out.split('\n') if l.startswith('|')]
for l in lines[:3]:
    print(l)

# 测试finance
print("\n=== finance sh600519 4 ===")
out = run_westock("finance sh600519 4")
lines = [l for l in out.split('\n') if l.startswith('|')]
for l in lines[:5]:
    print(l)

# 测试kline获取最新收盘价
print("\n=== kline sh600519 day 5 ===")
out = run_westock("kline sh600519 day 5")
lines = [l for l in out.split('\n') if l.startswith('|')]
for l in lines[:3]:
    print(l)

# 测试search
print("\n=== search 贵州茅台 ===")
out = run_westock("search 贵州茅台")
lines = [l for l in out.split('\n') if l.startswith('|')]
for l in lines[:3]:
    print(l)
