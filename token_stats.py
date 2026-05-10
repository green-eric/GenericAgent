\
#!/usr/bin/env python3
"""
GA Token 统计脚本 — 唯一入口
用法:
  python token_stats.py                          # 今日统计（自动保存到 memory/token_report.md）
  python token_stats.py --date 2026-05-09        # 指定日期
  python token_stats.py --week                   # 近7天
  python token_stats.py --month                  # 近30天（按月汇总）
  python token_stats.py --log                    # 同时解析 wechatapp.log
  python token_stats.py --csv ds_backend.csv     # 对比DS后台
  python token_stats.py --json                   # 输出JSON
"""
import os, sys, re, json, argparse, csv
from datetime import datetime, timedelta
from collections import defaultdict

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_RESPONSES_DIR = os.path.join(SCRIPT_DIR, "temp", "model_responses")
WECHATAPP_LOG = os.path.join(SCRIPT_DIR, "temp", "wechatapp.log")
MEMORY_DIR = os.path.join(SCRIPT_DIR, "memory")
REPORT_PATH = os.path.join(MEMORY_DIR, "token_report.md")

# ── deepseek-v4-flash 定价 ──
DS_CACHE_MISS = 1.0
DS_CACHE_HIT  = 0.02
DS_OUTPUT     = 2.0
# model_responses 估算用统一均价
PRICE_INPUT_PER_M  = 0.25
PRICE_OUTPUT_PER_M = 1.00
PRICE_INPUT_ORIG   = 1.0
PRICE_OUTPUT_ORIG  = 4.0
CHARS_PER_TOKEN    = 2.5
WARN_CALLS_DAY     = 500_000
WARN_COST_DAY      = 50.0


def scan_date(target_date):
    date_obj = datetime.strptime(target_date, "%Y-%m-%d").date()
    total_files = total_bytes = total_prompt_chars = total_response_chars = 0
    if not os.path.isdir(MODEL_RESPONSES_DIR):
        return _empty_row(target_date)
    for fn in os.listdir(MODEL_RESPONSES_DIR):
        fp = os.path.join(MODEL_RESPONSES_DIR, fn)
        if not os.path.isfile(fp):
            continue
        if datetime.fromtimestamp(os.path.getmtime(fp)).date() != date_obj:
            continue
        total_files += 1
        total_bytes += os.path.getsize(fp)
        try:
            with open(fp, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
        except Exception:
            continue
        in_prompt = in_response = False
        for line in content.split("\\n"):
            if "=== Prompt ===" in line:
                in_prompt, in_response = True, False; continue
            elif "=== Response ===" in line or "=== 回复 ===" in line:
                in_prompt, in_response = False, True; continue
            elif "=== End ===" in line:
                in_prompt = in_response = False; continue
            if in_prompt:
                total_prompt_chars += len(line) + 1
            elif in_response:
                total_response_chars += len(line) + 1
    input_tokens = int(total_prompt_chars / CHARS_PER_TOKEN)
    output_tokens = int(total_response_chars / CHARS_PER_TOKEN)
    calls = total_files * 3
    cost      = input_tokens / 1e6 * PRICE_INPUT_PER_M  + output_tokens / 1e6 * PRICE_OUTPUT_PER_M
    cost_orig = input_tokens / 1e6 * PRICE_INPUT_ORIG    + output_tokens / 1e6 * PRICE_OUTPUT_ORIG
    return {
        "date": target_date, "files": total_files, "calls": calls,
        "input_tokens": input_tokens, "output_tokens": output_tokens,
        "total_cost": cost, "total_cost_orig": cost_orig,
        "total_bytes": total_bytes, "source": "model_responses",
    }


def parse_wechatapp_log(target_date=None):
    if not os.path.exists(WECHATAPP_LOG):
        return []
    date_str = target_date or datetime.now().strftime("%Y-%m-%d")
    if len(date_str) > 5:
        date_str = date_str[5:]
    time_pat  = re.compile(r"(?:Process starting )?(\d{2}-\d{2} \d{2}:\d{2})")
    cache_pat = re.compile(r"\[Cache\]\s+input=(\d+)\s+creation=(\d+)\s+read=(\d+)")
    output_pat = re.compile(r"\[Output\]\s+tokens=(\d+)\s+stop_reason=(\S+)")
    records = []
    current_time = ""
    with open(WECHATAPP_LOG, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            tm = time_pat.search(line)
            if tm:
                current_time = tm.group(1)
            if not current_time or not current_time.startswith(date_str):
                continue
            c = cache_pat.search(line)
            if c:
                records.append({"time": current_time, "type": "cache",
                    "input": int(c.group(1)), "creation": int(c.group(2)), "read": int(c.group(3))})
                continue
            o = output_pat.search(line)
            if o:
                records.append({"time": current_time, "type": "output",
                    "tokens": int(o.group(1)), "stop_reason": o.group(2)})
    return records


def analyze_log_records(records):
    stats = {"requests": 0, "cache_misses": 0, "cache_hits": 0,
             "input_tokens": 0, "creation_tokens": 0, "read_tokens": 0, "output_tokens": 0}
    for r in records:
        if r["type"] == "cache":
            stats["requests"] += 1
            stats["input_tokens"] += r["input"]
            stats["creation_tokens"] += r["creation"]
            stats["read_tokens"] += r["read"]
            if r["creation"] > 0:
                stats["cache_misses"] += 1
            elif r["read"] > 0:
                stats["cache_hits"] += 1
        elif r["type"] == "output":
            stats["output_tokens"] += r["tokens"]
    return stats


def calc_log_cost(stats):
    miss = stats["creation_tokens"] / 1e6
    hit  = stats["read_tokens"] / 1e6
    out  = stats["output_tokens"] / 1e6
    return miss * DS_CACHE_MISS + hit * DS_CACHE_HIT + out * DS_OUTPUT


def parse_ds_csv(csv_path, target_date=None):
    if not os.path.exists(csv_path):
        return None
    date_str = target_date or datetime.now().strftime("%Y-%m-%d")
    if len(date_str) > 5:
        date_str = date_str[5:]
    rows = []
    with open(csv_path, "r", encoding="utf-8", errors="replace") as f:
        for row in csv.DictReader(f):
            utc = row.get("utc_date", "")
            if utc:
                try:
                    local = (datetime.strptime(utc, "%Y-%m-%d") + timedelta(hours=8)).strftime("%m-%d")
                except:
                    local = utc[-5:] if len(utc) >= 5 else utc
                if local != date_str:
                    continue
            rows.append(row)
    return rows


def _empty_row(date):
    return {"date": date, "files": 0, "calls": 0, "input_tokens": 0,
            "output_tokens": 0, "total_cost": 0, "total_cost_orig": 0,
            "total_bytes": 0, "source": "none"}


def format_report(today, week=None, month=None, log_stats=None, ds_rows=None):
    L = []
    L.append(f"# GA Token Report \\u2014 {today['date']}")
    L.append("")
    sources = ["model_responses"]
    if log_stats:
        sources.append("wechatapp.log")
    if ds_rows:
        sources.append("DS\\u540e\\u53f0")
    L.append(f"> \\u6570\\u636e\\u6765\\u6e90: {' + '.join(sources)}")
    L.append("")
    L.append("## \\u4eca\\u65e5\\u6982\\u89c8")
    L.append("| \\u6307\\u6807 | \\u503c |")
    L.append("|------|-----|")
    L.append(f"| \\u6587\\u4ef6\\u6570 | {today['files']} |")
    L.append(f"| \\u4f30\\u7b97\\u8c03\\u7528 | ~{today['calls']:,} |")
    L.append(f"| Input Tokens | ~{today['input_tokens']:,} |")
    L.append(f"| Output Tokens | ~{today['output_tokens']:,} |")
    L.append(f"| \\u4f30\\u7b97\\u8d39\\u7528(\\u6298) | \\u00a5{today['total_cost']:.2f} |")
    L.append(f"| \\u4f30\\u7b97\\u8d39\\u7528(\\u539f) | \\u00a5{today['total_cost_orig']:.2f} |")
    L.append(f"| \\u6570\\u636e\\u91cf | {today['total_bytes']/1024/1024:.1f} MB |")
    L.append("")
    alerts = []
    if today["calls"] > WARN_CALLS_DAY:
        alerts.append(f"\\u26a0\\ufe0f \\u8c03\\u7528\\u5f02\\u5e38: {today['calls']:,} > {WARN_CALLS_DAY:,}")
    if today["total_cost_orig"] > WARN_COST_DAY:
        alerts.append(f"\\u26a0\\ufe0f \\u8d39\\u7528\\u5f02\\u5e38: \\u00a5{today['total_cost_orig']:.2f} > \\u00a5{WARN_COST_DAY}")
    if alerts:
        L.append("## \\u26a0\\ufe0f \\u544a\\u8b66")
        for a in alerts:
            L.append(f"- {a}")
        L.append("")
    if log_stats:
        miss_rate = log_stats["cache_misses"] / log_stats["requests"] * 100 if log_stats["requests"] else 0
        cost_val = calc_log_cost(log_stats)
        L.append("## wechatapp.log \\u7cbe\\u786e\\u7edf\\u8ba1")
        L.append("| \\u6307\\u6807 | \\u503c |")
        L.append("|------|-----|")
        L.append(f"| \\u8bf7\\u6c42\\u6570 | {log_stats['requests']:,} |")
        L.append(f"| Cache Miss | {log_stats['cache_misses']:,} ({miss_rate:.1f}%) |")
        L.append(f"| Cache Hit | {log_stats['cache_hits']:,} ({100-miss_rate:.1f}%) |")
        L.append(f"| \\u8f93\\u5165 tokens | {log_stats['input_tokens']:,} |")
        L.append(f"| \\u8f93\\u51fa tokens | {log_stats['output_tokens']:,} |")
        L.append(f"| \\u7cbe\\u786e\\u8d39\\u7528 | \\u00a5{cost_val:.2f} |")
        L.append("")
    if ds_rows is not None:
        ds_total = sum(float(r.get("price", 0)) for r in ds_rows)
        ds_by_type = defaultdict(float)
        for r in ds_rows:
            ds_by_type[r.get("type", "")] += float(r.get("price", 0))
        est = today["total_cost"]
        diff = (est - ds_total) / ds_total * 100 if ds_total else 0
        L.append("## DS \\u540e\\u53f0\\u5bf9\\u6bd4")
        L.append("| \\u6307\\u6807 | \\u503c |")
        L.append("|------|-----|")
        L.append(f"| DS\\u540e\\u53f0\\u603b\\u989d | \\u00a5{ds_total:.2f} |")
        L.append(f"| \\u672c\\u5730\\u4f30\\u7b97 | \\u00a5{est:.2f} |")
        L.append(f"| \\u5dee\\u5f02 | {diff:+.1f}% |")
        for t, v in sorted(ds_by_type.items()):
            L.append(f"| \\u2014 {t} | \\u00a5{v:.2f} |")
        L.append("")
    if week:
        L.append("## \\u8fd17\\u5929\\u8d8b\\u52bf")
        L.append("| \\u65e5\\u671f | \\u6587\\u4ef6 | \\u8c03\\u7528 | Input | Output | \\u8d39\\u7528(\\u6298) | \\u8d39\\u7528(\\u539f) |")
        L.append("|------|------|------|-------|--------|----------|----------|")
        total_calls = total_cost = 0
        for d in week:
            L.append(f"| {d['date']} | {d['files']} | ~{d['calls']:,} | ~{d['input_tokens']:,} | ~{d['output_tokens']:,} | \\u00a5{d['total_cost']:.2f} | \\u00a5{d['total_cost_orig']:.2f} |")
            total_calls += d["calls"]
            total_cost += d["total_cost"]
        L.append(f"| **\\u5408\\u8ba1** | | **~{total_calls:,}** | | | **\\u00a5{total_cost:.2f}** | |")
        L.append("")
    if month:
        L.append("## \u8fd130\u5929\u8d8b\u52bf")
        L.append("| \u65e5\u671f | \u6587\u4ef6 | \u8c03\u7528 | Input | Output | \u8d39\u7528(\u6298) | \u8d39\u7528(\u539f) |")
        L.append("|------|------|------|-------|--------|----------|----------|")
        total_calls = total_cost = 0
        for d in month:
            L.append(f"| {d['date']} | {d['files']} | ~{d['calls']:,} | ~{d['input_tokens']:,} | ~{d['output_tokens']:,} | \u00a5{d['total_cost']:.2f} | \u00a5{d['total_cost_orig']:.2f} |")
            total_calls += d["calls"]
            total_cost += d["total_cost"]
        L.append(f"| **\u5408\u8ba1** | | **~{total_calls:,}** | | | **\u00a5{total_cost:.2f}** | |")
        L.append("")
    L.append("---")
    L.append("*\\u4e3b: LongCat-2.0-Preview(\\u514d\\u8d39) | \\u5907: deepseek-v4-flash | \\u811a\\u672c: token_stats.py*")
    return "\\n".join(L)


def main():
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description="GA Token \\u7edf\\u8ba1\\uff08\\u552f\\u4e00\\u811a\\u672c\\uff09")
    parser.add_argument("--date",   type=str, default=None,  help="\\u76ee\\u6807\\u65e5\\u671f YYYY-MM-DD")
    parser.add_argument("--week",   action="store_true",      help="\\u8fd17\\u5929")
    parser.add_argument("--month",  action="store_true",      help="\u8fd130\u5929\uff08\u6309\u6708\u6c47\u603b\uff09")
    parser.add_argument("--log",    action="store_true",      help="\\u540c\\u65f6\\u89e3\\u6790 wechatapp.log")
    parser.add_argument("--csv",    type=str, default=None,  help="DS\\u540e\\u53f0CSV\\u8def\\u5f84")
    parser.add_argument("--json",   action="store_true",      help="JSON\\u8f93\\u51fa")
    parser.add_argument("--output", type=str, default=None,  help="\\u4fdd\\u5b58\\u62a5\\u544a\\u8def\\u5f84")
    args = parser.parse_args()
    target = args.date or datetime.now().strftime("%Y-%m-%d")
    today = scan_date(target)
    log_stats = None
    if args.log:
        records = parse_wechatapp_log(target)
        log_stats = analyze_log_records(records)
    ds_rows = parse_ds_csv(args.csv, target) if args.csv else None
    week = None
    if args.week:
        week = []
        for i in range(7):
            d = (datetime.strptime(target, "%Y-%m-%d") - timedelta(days=i)).strftime("%Y-%m-%d")
            week.append(scan_date(d))
    month = None
    if args.month:
        month = []
        for i in range(30):
            d = (datetime.strptime(target, "%Y-%m-%d") - timedelta(days=i)).strftime("%Y-%m-%d")
            month.append(scan_date(d))

    if args.json:
        out = {"today": today, "log_stats": log_stats, "ds_rows_count": len(ds_rows) if ds_rows else 0}
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return
    report = format_report(today, week, month, log_stats, ds_rows)
    print(report)
    save_path = args.output or REPORT_PATH
    os.makedirs(os.path.dirname(save_path) or ".", exist_ok=True)
    with open(save_path, "w", encoding="utf-8") as f:
        f.write(report)
    print(f"\\n[OK] \\u62a5\\u544a\\u5df2\\u4fdd\\u5b58: {save_path}")


if __name__ == "__main__":
    main()
