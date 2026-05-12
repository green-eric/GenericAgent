#!/usr/bin/env python3
"""
GA Token 统计脚本 - 基于 llmcore usage_log.jsonl
数据源: memory/usage_log.jsonl (_record_usage 实时写入)
价格: 多模型人民币定价（见 MODEL_PRICES），汇率 1 USD ≈ 7.25 CNY

用法:
  python token_stats.py                          # 今日统计
  python token_stats.py --date 2026-05-09        # 指定日期
  python token_stats.py --week                   # 近7天
  python token_stats.py --month                  # 近30天
  python token_stats.py --all                    # 全部历史
  python token_stats.py --output report.md       # 指定输出文件
"""

import json, os, sys, argparse, datetime
from collections import defaultdict

# ── 配置 ──────────────────────────────────────────────────
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
USAGE_LOG = os.path.join(SCRIPT_DIR, 'memory', 'usage_log.jsonl')
REPORT_PATH = os.path.join(SCRIPT_DIR, 'memory', 'token_report.md')

# ── 模型价格表（每百万 token，人民币 ¥） ────────────────────
# 汇率按 1 USD ≈ 7.25 CNY；本地模型费用为 0
MODEL_PRICES = {
    # DeepSeek V3-Flash
    "deepseek-v3-flash":          {"input": 0.54,  "output": 1.81},
    "deepseek-v3-flash-0724":     {"input": 0.54,  "output": 1.81},
    "LongCat-2.0-Preview":        {"input": 0.54,  "output": 1.81},  # 同 DS V3-Flash 定价
    # Ollama 本地模型（免费）
    "gemma3:4b":                  {"input": 0.0,   "output": 0.0},
    "ollama/gemma3:4b":           {"input": 0.0,   "output": 0.0},
}
# 默认价格（未匹配到模型时fallback）
DEFAULT_PRICE_INPUT  = 0.54
DEFAULT_PRICE_OUTPUT = 1.81

# ── 读取 usage_log ────────────────────────────────────────
def load_log(date_filter=None, days_back=None):
    if not os.path.exists(USAGE_LOG):
        return []
    rows = []
    cutoff = None
    if days_back:
        cutoff = datetime.datetime.now() - datetime.timedelta(days=days_back)
    with open(USAGE_LOG, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
            except:
                continue
            ts_str = entry.get('ts', '')
            try:
                ts = datetime.datetime.fromisoformat(ts_str)
            except:
                continue
            if cutoff and ts < cutoff:
                continue
            if date_filter:
                if len(date_filter) == 5:
                    local_md = ts.strftime('%m-%d')
                else:
                    local_md = ts.strftime('%Y-%m-%d')
                if local_md != date_filter:
                    continue
            entry['_ts'] = ts
            rows.append(entry)
    return rows

# ── 按 model 分组聚合 ─────────────────────────────────────
def aggregate_by_model(rows):
    stats = defaultdict(lambda: {
        'calls': 0, 'input': 0, 'output': 0,
        'cached': 0, 'cache_creation': 0, 'cache_read': 0,
        'cost_input': 0.0, 'cost_output': 0.0, 'cost_total': 0.0,
    })
    for r in rows:
        model = r.get('model', 'unknown') or 'unknown'
        s = stats[model]
        s['calls'] += 1
        s['input'] += r.get('input', 0)
        s['output'] += r.get('output', 0)
        s['cached'] += r.get('cached', 0) or r.get('cache_read', 0)
        s['cache_creation'] += r.get('cache_creation', 0)
        s['cache_read'] += r.get('cache_read', 0)
        # 按模型查价格表，未匹配用默认
        mp = MODEL_PRICES.get(model, {"input": DEFAULT_PRICE_INPUT, "output": DEFAULT_PRICE_OUTPUT})
        s['cost_input'] += r.get('input', 0) * mp["input"] / 1_000_000
        s['cost_output'] += r.get('output', 0) * mp["output"] / 1_000_000
    for s in stats.values():
        s['cost_total'] = s['cost_input'] + s['cost_output']
    return dict(stats)

def aggregate_total(model_stats):
    total = {'calls': 0, 'input': 0, 'output': 0, 'cached': 0,
             'cache_creation': 0, 'cache_read': 0,
             'cost_input': 0.0, 'cost_output': 0.0, 'cost_total': 0.0}
    for s in model_stats.values():
        for k in total:
            total[k] += s[k]
    return total

# ── 按日期分组 ────────────────────────────────────────────
def group_by_date(rows):
    groups = defaultdict(list)
    for r in rows:
        d = r['_ts'].strftime('%Y-%m-%d')
        groups[d].append(r)
    return dict(sorted(groups.items()))

# ── 格式化 ────────────────────────────────────────────────
def fmt_num(n):
    if n >= 1_000_000:
        return f"{n/1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n/1_000:.1f}K"
    return str(int(n))

def format_model_table(model_stats, total):
    if not model_stats:
        return "_暂无数据_\n"
    lines = []
    lines.append("| 模型 | 调用 | 输入 | 含缓存 | 输出 | Cache创建 | 输入费 | 输出费 | 总费用 |")
    lines.append("|------|-----:|-----:|------:|-----:|----------:|-------:|-------:|-------:|")
    for model, s in sorted(model_stats.items(), key=lambda x: -x[1]['cost_total']):
        with_cache = s['input'] + s['cache_read']
        lines.append(
            f"| `{model}` | {s['calls']} | {fmt_num(s['input'])} | {fmt_num(with_cache)} "
            f"| {fmt_num(s['output'])} | {fmt_num(s['cache_creation'])} "
            f"| ¥{s['cost_input']:.4f} | ¥{s['cost_output']:.4f} | **¥{s['cost_total']:.4f}** |"
        )
    with_cache_total = total['input'] + total['cache_read']
    lines.append(
        f"| **合计** | **{total['calls']}** | **{fmt_num(total['input'])}** | **{fmt_num(with_cache_total)}** "
        f"| **{fmt_num(total['output'])}** | **{fmt_num(total['cache_creation'])}** "
        f"| **¥{total['cost_input']:.4f}** | **¥{total['cost_output']:.4f}** | **¥{total['cost_total']:.4f}** |"
    )
    lines.append("")
    return "\n".join(lines)

def format_report(today_stats, today_total, week_stats=None, week_total=None,
                  month_stats=None, month_total=None, all_daily=None):
    now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M')
    lines = []
    lines.append(f"# GA Token 统计报告")
    price_info = " | ".join(f"{m}: ¥{p['input']}/¥{p['output']} per M" for m, p in list(MODEL_PRICES.items())[:3])
    lines.append(f"> 生成时间: {now} | 价格: {price_info}")
    lines.append("")
    lines.append(f"## 今日")
    lines.append(format_model_table(today_stats, today_total))
    if week_stats is not None:
        lines.append(f"## 近7天汇总")
        lines.append(format_model_table(week_stats, week_total))
    if month_stats is not None:
        lines.append(f"## 近30天汇总")
        lines.append(format_model_table(month_stats, month_total))
    if all_daily:
        lines.append(f"## 每日趋势")
        lines.append("| 日期 | 模型 | 调用 | 输入 | 输出 | 缓存命中 | 费用 |")
        lines.append("|------|------|-----:|-----:|-----:|---------:|-----:|")
        for date_str, stats in list(all_daily.items())[-14:]:
            total = aggregate_total(stats)
            models = ', '.join(sorted(stats.keys()))
            lines.append(f"| {date_str} | {models} | {total['calls']} | {fmt_num(total['input'])} | {fmt_num(total['output'])} | {fmt_num(total['cached'])} | ¥{total['cost_total']:.4f} |")
    return "\n".join(lines)

# ── 主入口 ────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description='GA Token 统计')
    parser.add_argument('--date', help='指定日期 MM-DD 或 YYYY-MM-DD')
    parser.add_argument('--week', action='store_true', help='近7天')
    parser.add_argument('--month', action='store_true', help='近30天')
    parser.add_argument('--all', action='store_true', help='全部历史（按日展示）')
    parser.add_argument('--output', help='输出文件路径')
    args = parser.parse_args()

    today_str = datetime.datetime.now().strftime('%Y-%m-%d')
    today_rows = load_log(date_filter=today_str)
    today_stats = aggregate_by_model(today_rows)
    today_total = aggregate_total(today_stats)

    week_stats = week_total = None
    if args.week or args.all:
        week_rows = load_log(days_back=7)
        week_stats = aggregate_by_model(week_rows)
        week_total = aggregate_total(week_stats)

    month_stats = month_total = None
    if args.month or args.all:
        month_rows = load_log(days_back=30)
        month_stats = aggregate_by_model(month_rows)
        month_total = aggregate_total(month_stats)

    all_daily = None
    if args.all:
        all_rows = load_log()
        all_daily = {}
        for date_str, rows in group_by_date(all_rows).items():
            all_daily[date_str] = aggregate_by_model(rows)

    if args.date:
        rows = load_log(date_filter=args.date)
        stats = aggregate_by_model(rows)
        total = aggregate_total(stats)
        report = f"# Token 统计 - {args.date}\n\n"
        report += format_model_table(stats, total)
    else:
        report = format_report(today_stats, today_total, week_stats, week_total,
                               month_stats, month_total, all_daily)

    # 安全输出：GBK 控制台不支持 ¥ 时回退为 RMB
    try:
        print(report)
    except UnicodeEncodeError:
        print(report.replace('¥', 'RMB'))
    save_path = args.output or REPORT_PATH
    os.makedirs(os.path.dirname(save_path) or '.', exist_ok=True)
    with open(save_path, 'w', encoding='utf-8') as f:
        f.write(report)
    print(f"\n[OK] 报告已保存: {save_path}")

if __name__ == '__main__':
    main()
