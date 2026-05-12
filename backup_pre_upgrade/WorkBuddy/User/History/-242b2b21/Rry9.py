#!/usr/bin/env python3
"""统计 Claude JSONL 日志中的 token 用量 - 适配 OpenCode 格式"""

import json
import os
import glob
from collections import defaultdict
from datetime import datetime

base = os.path.expanduser('~/.claude')
patterns = [
    os.path.join(base, 'transcripts', '*.jsonl'),
    os.path.join(base, 'projects', '**', '*.jsonl'),
    os.path.join(base, 'history.jsonl'),
]

total_input = 0
total_output = 0
model_stats = defaultdict(lambda: {'input': 0, 'output': 0, 'cost': 0.0, 'calls': 0})
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
                    
                    if not isinstance(rec, dict):
                        continue
                    
                    # OpenCode transcript format - look for usage in various fields
                    usage = None
                    model = ''
                    
                    # Check all possible fields for usage/token data
                    for key in ['usage', 'messageUsage', 'tokenUsage', 'costDetails']:
                        if key in rec and isinstance(rec[key], dict):
                            usage = rec[key]
                            break
                    
                    if 'model' in rec and isinstance(rec['model'], str):
                        model = rec['model']
                    
                    # Also check nested fields like result.usage, response.usage etc.
                    if not usage:
                        for v in rec.values():
                            if isinstance(v, dict) and ('input_tokens' in v or 'inputTokens' in v or 'cost' in v):
                                usage = v
                                break
                    
                    # If we found usage data with tokens
                    if usage and isinstance(usage, dict):
                        inp = (usage.get('input_tokens', 0) or 
                               usage.get('inputTokens', 0) or 
                               usage.get('prompt_tokens', 0) or 0)
                        out = (usage.get('output_tokens', 0) or 
                              usage.get('outputTokens', 0) or 
                              usage.get('completion_tokens', 0) or 0)
                        
                        if inp > 0 or out > 0:
                            total_input += inp
                            total_output += out
                            records_processed += 1
                            
                            m = model or rec.get('type') or 'unknown'
                            price = pricing.get(m, {'input': 3.0, 'output': 15.0})
                            cost = inp * price['input'] / 1e6 + out * price['output'] / 1e6
                            
                            model_stats[m]['input'] += inp
                            model_stats[m]['output'] += out
                            model_stats[m]['cost'] += cost
                            model_stats[m]['calls'] += 1
                            
                            ts = rec.get('timestamp')
                            if ts:
                                try:
                                    d = str(ts)[:10]
                                    date_stats[d]['input'] += inp
                                    date_stats[d]['output'] += out
                                    date_stats[d]['cost'] += cost
                                except Exception:
                                    pass
        except Exception as e:
            pass


print('=' * 60)
print('  Token 用量统计报告')
print('=' * 60)
print(f'\n扫描文件数: {file_count}')
print(f'处理记录数: {records_processed}')
print()
print(f'总输入Token:   {total_input:>14,}')
print(f'总输出Token:   {total_output:>14,}')
print(f'总Token合计:   {total_input + total_output:>14,}')

if model_stats:
    print('\n' + '-' * 60)
    print('  按类型/模型统计（按费用排序）')
    print('-' * 60)
    total_cost = 0
    print(f"  {'类型/模型':<32} {'调用次数':>6} {'输入Token':>12} {'输出Token':>12} {'费用(USD)':>10}")
    print('  ' + '-' * 76)
    for m, s in sorted(model_stats.items(), key=lambda x: -x[1]['cost']):
        c = s['cost']
        total_cost += c
        name = m[:30] + '..' if len(m) > 32 else m
        print(f"  {name:<32} {s['calls']:>6} {s['input']:>12,} {s['output']:>12,} ${c:>9.2f}")
    print('  ' + '-' * 76)
    print(f"  {'合计':<32} {'':>6} {total_input:>12,} {total_output:>12,} ${total_cost:>9.2f}")

if date_stats:
    print('\n' + '-' * 60)
    print('  最近7天用量趋势')
    print('-' * 60)
    recent_days = sorted(date_stats.keys())[-7:]
    if recent_days:
        print(f"  {'日期':<14} {'输入Token':>12} {'输出Token':>12} {'费用(USD)':>10}")
        print('  ' + '-' * 50)
        day_sum_c = 0
        day_sum_i = 0
        day_sum_o = 0
        for d in recent_days:
            s = date_stats[d]
            day_sum_c += s['cost']
            day_sum_i += s['input']
            day_sum_o += s['output']
            print(f"  {d:<14} {s['input']:>12,} {s['output']:>12,} ${s['cost']:>9.2f}")
        print('  ' + '-' * 50)
        print(f"  {'小计':<14} {day_sum_i:>12,} {day_sum_o:>12,} ${day_sum_c:>9.2f}")

# Also estimate based on file sizes if no structured data
if records_processed == 0 and file_count > 0:
    print('\n' + '-' * 60)
    print('  注意: 未找到结构化token数据，基于文件大小估算')
    print('-' * 60)
    
    total_size_bytes = 0
    file_details = []
    
    for pat in patterns:
        for f in glob.glob(pat, recursive=True):
            sz = os.path.getsize(f)
            total_size_bytes += sz
            dt = datetime.fromtimestamp(os.path.getmtime(f))
            file_details.append((f, sz, dt))
    
    # Rough estimation: ~5 chars per token average
    estimated_tokens = total_size_bytes // 5
    
    # Rough cost estimation at $3/M input + $15/M output (Sonnet rates)
    # Assume 70% input, 30% output
    est_input = int(estimated_tokens * 0.7)
    est_output = int(estimated_tokens * 0.3)
    est_cost = est_input * 3 / 1e6 + est_output * 15 / 1e6
    
    print(f'\n总日志大小:     {total_size_bytes / 1024:.1f} KB ({total_size_bytes:,} bytes)')
    print(f'估算总Token:     {estimated_tokens:,} (约5字节/token)')
    print(f'估算输入Token:   {est_input:,}')
    print(f'估算输出Token:   {est_output:,}')
    print(f'估算总费用:      ${est_cost:.2f}')
    
    print(f'\n最近修改的文件:')
    file_details.sort(key=lambda x: x[2], reverse=True)
    for fp, sz, dt in file_details[:10]:
        fn = os.path.basename(fp)
        print(f'  {dt.strftime("%Y-%m-%d %H:%M")}  {sz/1024:>7.1f}KB  {fn}')
