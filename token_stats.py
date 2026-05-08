#!/usr/bin/env python3
"""GA Token 每日统计脚本"""
import os, sys, json, argparse
from datetime import datetime, timedelta

MODEL_RESPONSES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "temp", "model_responses")

PRICE_INPUT_PER_M = 0.25
PRICE_OUTPUT_PER_M = 1.00
PRICE_INPUT_ORIGINAL = 1.0
PRICE_OUTPUT_ORIGINAL = 4.0
WARN_CALLS_DAY = 500_000
WARN_COST_DAY = 50.0


def scan_date(target_date):
    date_obj = datetime.strptime(target_date, "%Y-%m-%d").date()
    total_files = 0
    total_bytes = 0
    total_prompt_chars = 0
    total_response_chars = 0

    if not os.path.isdir(MODEL_RESPONSES_DIR):
        return {"files": 0, "calls": 0, "input_tokens": 0, "output_tokens": 0,
                "total_cost": 0, "total_cost_orig": 0, "total_bytes": 0, "date": target_date}

    for fn in os.listdir(MODEL_RESPONSES_DIR):
        fp = os.path.join(MODEL_RESPONSES_DIR, fn)
        if not os.path.isfile(fp):
            continue
        mtime = datetime.fromtimestamp(os.path.getmtime(fp)).date()
        if mtime != date_obj:
            continue
        total_files += 1
        total_bytes += os.path.getsize(fp)
        try:
            with open(fp, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
        except Exception:
            continue
        in_prompt = False
        in_response = False
        for line in content.split("\n"):
            if "=== Prompt ===" in line:
                in_prompt = True; in_response = False; continue
            elif "=== Response ===" in line or "=== 回复 ===" in line:
                in_prompt = False; in_response = True; continue
            elif "=== End ===" in line:
                in_prompt = False; in_response = False; continue
            if in_prompt:
                total_prompt_chars += len(line) + 1
            elif in_response:
                total_response_chars += len(line) + 1

    CHARS_PER_TOKEN = 2.5
    input_tokens = int(total_prompt_chars / CHARS_PER_TOKEN)
    output_tokens = int(total_response_chars / CHARS_PER_TOKEN)
    estimated_calls = total_files * 3
    input_cost = (input_tokens / 1e6) * PRICE_INPUT_PER_M
    output_cost = (output_tokens / 1e6) * PRICE_OUTPUT_PER_M
    input_cost_orig = (input_tokens / 1e6) * PRICE_INPUT_ORIGINAL
    output_cost_orig = (output_tokens / 1e6) * PRICE_OUTPUT_ORIGINAL

    return {
        "date": target_date, "files": total_files, "calls": estimated_calls,
        "input_tokens": input_tokens, "output_tokens": output_tokens,
        "total_cost": input_cost + output_cost,
        "total_cost_orig": input_cost_orig + output_cost_orig,
        "total_bytes": total_bytes,
    }


def format_report(data, week_data=None):
    lines = []
    lines.append(f"# [REPORT] GA Token 日报 \u2014 {data['date']}")
    lines.append("")
    lines.append("## Today")
    lines.append(f"| Metric | Value |")
    lines.append(f"|------|------|")
    lines.append(f"| 文件数 | {data['files']} |")
    lines.append(f"| 估算调用 | ~{data['calls']:,} |")
    lines.append(f"| Input Tokens | ~{data['input_tokens']:,} |")
    lines.append(f"| Output Tokens | ~{data['output_tokens']:,} |")
    lines.append(f"| 费用(2.5折) | ¥{data['total_cost']:.2f} |")
    lines.append(f"| 费用(原价) | ¥{data['total_cost_orig']:.2f} |")
    lines.append(f"| 数据量 | {data['total_bytes']/1024/1024:.1f} MB |")
    lines.append("")
    if data["calls"] > WARN_CALLS_DAY:
        lines.append(f"\u26a0\ufe0f 调用次数异常: {data['calls']:,} > {WARN_CALLS_DAY:,}")
    if data["total_cost_orig"] > WARN_COST_DAY:
        lines.append(f"\u26a0\ufe0f 费用异常: ¥{data['total_cost_orig']:.2f} > ¥{WARN_COST_DAY}")
    if week_data:
        lines.append("## Last 7 Days")
        lines.append("| 日期 | 文件 | 调用 | Input | Output | 费用(折) | 费用(原) |")
        lines.append("|------|------|------|-------|--------|----------|----------|")
        for d in week_data:
            lines.append(f"| {d['date']} | {d['files']} | ~{d['calls']:,} | ~{d['input_tokens']:,} | ~{d['output_tokens']:,} | ¥{d['total_cost']:.2f} | ¥{d['total_cost_orig']:.2f} |")
    lines.append("\n---\n*deepseek-v4-pro | 2.5折优惠至 2026-05-31 | 数据基于 model_responses 估算*")
    return "\n".join(lines)


def main():
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

    parser = argparse.ArgumentParser(description="GA Token 每日统计")
    parser.add_argument("--date", type=str, default=None)
    parser.add_argument("--week", action="store_true")
    parser.add_argument("--output", type=str, default=None)
    args = parser.parse_args()
    target = args.date or datetime.now().strftime("%Y-%m-%d")
    data = scan_date(target)
    week_data = None
    if args.week:
        week_data = []
        for i in range(7):
            d = (datetime.strptime(target, "%Y-%m-%d") - timedelta(days=i)).strftime("%Y-%m-%d")
            week_data.append(scan_date(d))
    report = format_report(data, week_data)
    print(report)
    if args.output:
        os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(report)
        print(f"\n[OK] 报告已保存: {args.output}")


if __name__ == "__main__":
    main()
