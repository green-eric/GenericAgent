#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""检查westock-data finance是否有总股本字段"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ['PYTHONIOENCODING'] = 'utf-8'

import subprocess
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

def run_westock(args):
    r = subprocess.run(
        f'npx --yes westock-data-skillhub@latest {args}',
        shell=True, capture_output=True, text=True, encoding='utf-8', timeout=60
    )
    output = r.stdout + r.stderr
    lines = [l.strip() for l in output.split('\n') if l.strip().startswith('|')]
    return lines

# finance 所有字段的值
print("=== finance sh600519 1 (所有字段值) ===")
lines = run_westock("finance sh600519 1")
if lines:
    header = [c.strip() for c in lines[0].split('|')[1:-1]]
    if len(lines) >= 3:
        values = [c.strip() for c in lines[2].split('|')[1:-1]]
        for h, v in zip(header, values):
            print(f"  {h}: {v}")

# 检查是否有share/capital相关字段
print("\n=== 搜索总股本相关字段 ===")
keywords = ['share', 'capital', 'total', 'volume', 'amount', 'outstanding', 'listed']
for kw in keywords:
    print(f"  {kw}: ", end="")
    found = []
    lines = run_westock("finance sh600519 1")
    if lines:
        header = [c.strip() for c in lines[0].split('|')[1:-1]]
        for h in header:
            if kw.lower() in h.lower():
                found.append(h)
    print(", ".join(found) if found else "无")

# 检查profile中regCapital是否是总股本
print("\n=== profile中的regCapital ===")
lines = run_westock("profile sh600519")
if lines:
    header = [c.strip() for c in lines[0].split('|')[1:-1]]
    if len(lines) >= 3:
        values = [c.strip() for c in lines[2].split('|')[1:-1]]
        for h, v in zip(header, values):
            if 'capital' in h.lower() or 'reg' in h.lower():
                print(f"  {h}: {v}")

# 用收盘价 * regCapital 估算总市值
print("\n=== 估算总市值 ===")
# kline last price
lines = run_westock("kline sh600519 day 1")
if lines:
    header = [c.strip() for c in lines[0].split('|')[1:-1]]
    if len(lines) >= 3:
        values = [c.strip() for c in lines[2].split('|')[1:-1]]
        h2v = dict(zip(header, values))
        last_price = float(h2v.get('last', 0))
        print(f"  收盘价: {last_price}")

# profile regCapital
lines = run_westock("profile sh600519")
if lines:
    header = [c.strip() for c in lines[0].split('|')[1:-1]]
    if len(lines) >= 3:
        values = [c.strip() for c in lines[2].split('|')[1:-1]]
        h2v = dict(zip(header, values))
        reg_capital = float(h2v.get('regCapital', 0))
        print(f"  regCapital: {reg_capital} (万元)")
        # regCapital 单位是万元
        total_mv = last_price * reg_capital * 10000  # 元
        print(f"  估算总市值: {total_mv:,.0f} 元 = {total_mv/1e8:,.2f} 亿元")
        print(f"  实际总市值约: 1.7 万亿 (需要确认regCapital单位)")

# 尝试用finance的NPParentCompanyOwners计算PE
print("\n=== 用finance净利润计算PE ===")
lines = run_westock("finance sh600519 1")
if lines:
    header = [c.strip() for c in lines[0].split('|')[1:-1]]
    if len(lines) >= 3:
        values = [c.strip() for c in lines[2].split('|')[1:-1]]
        h2v = dict(zip(header, values))
        np_parent = float(h2v.get('NPParentCompanyOwners', 0))
        np_ttm = float(h2v.get('NPParentCompanyOwnersTTM', 0))
        print(f"  NPParentCompanyOwners: {np_parent}")
        print(f"  NPParentCompanyOwnersTTM: {np_ttm}")
        if np_ttm > 0 and total_mv > 0:
            pe = total_mv / np_ttm
            print(f"  PE-TTM (估算): {pe:.2f}")
