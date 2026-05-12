#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""测试westock-data profile解析"""
import subprocess

def _westock_profile(symbol):
    try:
        if not (symbol.startswith('sh') or symbol.startswith('sz') or symbol.startswith('bj')):
            if symbol.startswith('6'):
                wcode = 'sh' + symbol
            elif symbol.startswith(('0', '3')):
                wcode = 'sz' + symbol
            else:
                wcode = 'bj' + symbol
        else:
            wcode = symbol

        print(f"Running: npx --yes westock-data-skillhub@latest profile {wcode}")
        r = subprocess.run(
            ['npx', '--yes', 'westock-data-skillhub@latest', 'profile', wcode],
            capture_output=True, text=True, encoding='utf-8', timeout=30
        )
        output = r.stdout + r.stderr
        print(f"Raw output (first 500 chars):\n{output[:500]}")
        
        lines = [l.strip() for l in output.split('\n') if l.strip().startswith('|')]
        print(f"\nTable lines: {len(lines)}")
        for i, l in enumerate(lines[:3]):
            print(f"  Line {i}: {l[:120]}")
        
        if len(lines) >= 2:
            header = [c.strip() for c in lines[0].split('|')[1:-1]]
            values = [c.strip() for c in lines[1].split('|')[1:-1]]
            print(f"\nHeaders: {header}")
            print(f"Values: {values}")
            
            result = {}
            for h, v in zip(header, values):
                h_lower = h.lower()
                if 'name' in h_lower and 'code' not in h_lower:
                    result['name'] = v
                elif 'industry' in h_lower:
                    result['industry'] = v
            print(f"Result: {result}")
            return result
    except Exception as e:
        print(f"Exception: {e}")
    return None

_westock_profile('600519')
