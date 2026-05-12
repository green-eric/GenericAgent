#!/usr/bin/env python3
"""统计 Claude JSONL 日志中的 token 用量"""

import json
import os
import re
import glob
from collections import defaultdict
from datetime import datetime

# Scan all Claude JSONL logs
base = os.path.expanduser('~/.claude')
patterns = [
    os.path.join(base, 'projects', '**', '*.jsonl'),
    os.path.join(base, 'transcripts', '*.jsonl'),
    os.path.join(base, 'history.jsonl'),
]

total_input = 0
total_output = 0
total_cache_read = 0
total_cache_creation = 0
model_stats = defaultdict(lambda: {'input': 0, 'output': 0, 'cache_read': 0, 'cache_creation': 0, 'cost': 0.0, 'calls': 0})
date_stats = defaultdict(lambda: {'input': 0, 'output': 0, 'cost': 0.0})
file_count = 0
records_processed = 0

# Claude pricing (per 1M tokens)
pricing = {
    'claude-opus-4-20250514': {'input': 15.0, 'output': 75.0},
    'claude-sonnet-4-20250514': {'input': 3.0, 'output': 15.0},
    'claude-haiku-3-5-20241022': {'input': 0.8, 'output': 4.0},
}

for pat in patterns:
    for f in glob.glob(pat, recursive=True):
        file_count += 1
        try:
            with open(f, 'r', encoding='utf-8') as fh:
                for line in fh:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        rec = json.loads(line)
                    except Exception:
                        continue
                    
                    usage = None
                    model = ''
                    
                    if isinstance(rec, dict):
                        if 'usage' in rec and isinstance(rec['usage'], dict):
                            usage = rec['usage']
                        elif 'messageUsage' in rec and isinstance(rec['messageUsage'], dict):
                            usage = rec['messageUsage']
                        
                        if 'model' in rec:
                            model = str(rec.get('model', ''))
                        elif rec.get('type') == 'summary':
                            model = str(rec.get('model', ''))
                    
                    if usage and isinstance(usage, dict):
                        inp = usage.get('input_tokens', 0) or usage.get('inputTokens', 0) or 0
                        out = usage.get('output_tokens', 0) or usage.get('outputTokens', 0) or 0
                        cache_read = usage.get('cache_read_input_tokens', 0) or usage.get('cacheReadInputTokens', 0) or 0
                        cache_creation = usage.get('cache_creation_input_tokens', 0) or usage.get('cacheCreationInputTokens', 0) or 0
                        
                        total_input += inp + cache_read + cache_creation
                        total_output += out
                        total_cache_read += cache_read
                        total_cache_creation += cache_creation
                        records_processed += 1
                        
                        m = model or 'unknown'
                        price = pricing.get(m, {'input': 3.0, 'output': 15.0})
                        cost = (inp + cache_creation) * price['input'] / 1e6 + cache_read * price['input'] * 0.1 / 1e6 + out * price['output'] / 1e6
                        
                        model_stats[m]['input'] += inp + cache_read + cache_creation
                        model_stats[m]['output'] += out
                        model_stats[m]['cache_read'] += cache_read
                        model_stats[m]['cache_creation'] += cache_creation
                        model_stats[m]['cost'] += cost
                        model_stats[m]['calls'] += 1
                        
                        dt = rec.get('timestamp') or rec.get('date') or rec.get('time')
                        if dt:
                            try:
                                if isinstance(dt, (int, float)):
                                    d = datetime.fromtimestamp(dt).strftime('%Y-%m-%d')
                                else:
                                    d = str(dt)[:10]
                                date_stats[d]['input'] += inp
                                date_stats[d]['output'] += out
                                date_stats[d]['cost'] += cost
                            except Exception:
                                pass
        except Exception as e:
            pass


print('=' * 55)
print('  Claude Token 用量统计报告')
print('=' * 55)
print(f'\n扫描文件数: {file_count}')
print(f'处理记录数: {records_processed}')
print()
print(f'总输入Token:   {total_input:>12,}')
print(f'  - 常规输入:      {total_input - total_cache_read - total_cache_creation:>10,}')
print(f'  - 缓存读取:      {total_cache_read:>10,}')
print(f'  - 缓存写入:      {total_cache_creation:>10,}')
print(f'总输出Token:   {total_output:>12,}')
print(f'总Token合计:   {total_input + total_output:>12,}')

if model_stats:
    print('\n' + '-' * 55)
    print('  按模型统计（按费用排序）')
    print('-' * 55)
    total_cost = 0
    print(f"{'模型名称':<35} {'调用次数':>6} {'输入Token':>12} {'输出Token':>12} {'费用(USD)':>10}")
    print('-' * 77)
    for m, s in sorted(model_stats.items(), key=lambda x: -x[1]['cost']):
        c = s['cost']
        total_cost += c
        name = m[:33] + '..' if len(m) > 35 else m
        print(f'{name:<35} {s["calls"]:>6} {s["input"]:>12,} {s["output"]:>12,} ${c:>9.2f}')
    print('-' * 77)
    print(f"{'合计':<35} {'':>6} {total_input:>12,} {total_output:>12,} ${total_cost:>9.2f}")

if date_stats:
    print('\n' + '-' * 55)
    print('  最近7天用量趋势')
    print('-' * 55)
    recent_days = sorted(date_stats.keys())[-7:]
    if recent_days:
        print(f"{'日期':<14} {'输入Token':>12} {'输出Token':>12} {'费用(USD)':>10}")
        print('-' * 50)
        day_cost_sum = 0
        for d in recent_days:
            s = date_stats[d]
            day_cost_sum += s['cost']
            print(f'{d:<14} {s["input"]:>12,} {s["output"]:>12,} ${s["cost"]:>9.2f}')
        print('-' * 50)
        print(f"{'小计':<14} {'':>12} {'':>12} ${day_cost_sum:>9.2f}")
