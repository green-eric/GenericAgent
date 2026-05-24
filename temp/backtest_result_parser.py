# backtest_result_parser.py - file_monitor_v3回测结果自动解析
# 功能: 监控autonomous_reports/auto_bt_*.json → 提取指标 → 写入PG → 生成Markdown摘要
# 依赖: sqlite3(standard library), file_monitor_v3(可选，用于获取最新结果)

import os
import sys
import json
import time
import glob
from datetime import datetime
from pathlib import Path

# ── 配置 ──────────────────────────────────────────────────────────
REPORTS_DIR = "./autonomous_reports"
DB_PATH = os.path.join(REPORTS_DIR, "backtest_results.db")  # SQLite本地存储

# ── 结果文件发现 ────────────────────────────────────────────────────

def find_result_files(directory=REPORTS_DIR, pattern="auto_bt_*.json"):
    """查找所有回测结果JSON文件，按时间排序"""
    files = glob.glob(os.path.join(directory, pattern))
    files.sort(key=os.path.getmtime)
    return files

def load_result(filepath):
    """加载单个回测结果JSON"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"[Parser] [FAIL] 加载失败 {filepath}: {e}")
        return None

# ── 指标提取 ──────────────────────────────────────────────────────

def extract_metrics(data, filepath=""):
    """
    从回测结果JSON中提取标准化指标
    兼容多种格式: v3标准格式(summary包装) / 扁平格式(字段在顶层) / ic_result格式
    """
    metrics = {
        "source_file": data.get("result_file", filepath),
        "timestamp": data.get("timestamp", datetime.now().isoformat()),
        "mode": data.get("mode", data.get("strategy", "unknown")),
        "start_date": data.get("start_date", ""),
        "end_date": data.get("end_date", ""),
        "elapsed_seconds": 0,
        "ic_mean": None,
        "ic_std": None,
        "ic_positive_pct": None,
        "total_return": None,
        "sharpe_ratio": None,
        "max_drawdown": None,
        "win_rate": None,
        "top_n": None,
        "min_score": None,
        "status": "unknown",
    }
    
    # 从summary提取(v3标准格式: 字段包装在summary中)
    summary = data.get("summary", {})
    if summary:
        metrics["ic_mean"] = summary.get("ic_mean")
        metrics["total_return"] = summary.get("total_return")
        metrics["sharpe_ratio"] = summary.get("sharpe_ratio")
        metrics["max_drawdown"] = summary.get("max_drawdown")
        metrics["win_rate"] = summary.get("win_rate")
        metrics["elapsed_seconds"] = summary.get("elapsed", data.get("elapsed_seconds", 0))
    
    # 从顶层提取(扁平格式: 字段直接在顶层)
    if metrics["total_return"] is None:
        metrics["total_return"] = data.get("total_return")
    if metrics["sharpe_ratio"] is None:
        metrics["sharpe_ratio"] = data.get("sharpe_ratio")
    if metrics["max_drawdown"] is None:
        metrics["max_drawdown"] = data.get("max_drawdown")
    if metrics["win_rate"] is None:
        metrics["win_rate"] = data.get("win_rate")
    if metrics["elapsed_seconds"] == 0:
        metrics["elapsed_seconds"] = data.get("elapsed_seconds", 0)
    
    # 从顶层提取(ic_result格式)
    if metrics["ic_mean"] is None:
        metrics["ic_mean"] = data.get("avg_ic")
    if metrics["ic_std"] is None:
        metrics["ic_std"] = data.get("ic_std")
    if metrics["ic_positive_pct"] is None:
        metrics["ic_positive_pct"] = data.get("ic_positive_pct")
    
    # 从meta提取
    meta = data.get("meta", {})
    if meta:
        if metrics["top_n"] is None:
            metrics["top_n"] = meta.get("top_n")
        if metrics["min_score"] is None:
            metrics["min_score"] = meta.get("min_score")
    
    # 从顶层提取参数
    if metrics["top_n"] is None:
        metrics["top_n"] = data.get("top_n")
    if metrics["min_score"] is None:
        metrics["min_score"] = data.get("min_score")
    
    # 从stdout_tail正则提取IC指标（兼容stdout输出格式）
    if metrics["ic_mean"] is None or metrics["total_return"] is None:
        stdout = data.get("stdout_tail", "")
        if stdout:
            import re
            # IC 均值: "IC 均值: +0.1880" 或 "IC均值: +0.1880"
            m = re.search(r'IC\s*均值:\s*([+-]?\d+\.?\d*)', stdout)
            if m and metrics["ic_mean"] is None:
                metrics["ic_mean"] = float(m.group(1))
            # IC 标准差: "IC 标准差: 0.0199"
            m = re.search(r'IC\s*标准差:\s*([+-]?\d+\.?\d*)', stdout)
            if m and metrics["ic_std"] is None:
                metrics["ic_std"] = float(m.group(1))
            # IC 正占比: "IC 正占比: 100.0%"
            m = re.search(r'IC\s*正占比:\s*([\d.]+)%', stdout)
            if m and metrics["ic_positive_pct"] is None:
                metrics["ic_positive_pct"] = float(m.group(1))
            # 总收益 / 夏普 / 回撤（stdout中如有）
            m = re.search(r'总收益[：:]\s*([+-]?\d+\.?\d*)%?', stdout)
            if m and metrics["total_return"] is None:
                metrics["total_return"] = float(m.group(1))
            m = re.search(r'夏普[比率]*[：:]\s*([+-]?\d+\.?\d*)', stdout)
            if m and metrics["sharpe_ratio"] is None:
                metrics["sharpe_ratio"] = float(m.group(1))
            m = re.search(r'最大回撤[：:]\s*([+-]?\d+\.?\d*)%?', stdout)
            if m and metrics["max_drawdown"] is None:
                metrics["max_drawdown"] = float(m.group(1))

    # 状态判断：有核心指标才算success，无IC数据且stdout提示失败则标记failed
    stdout = data.get("stdout_tail", "")
    has_no_ic = stdout and ('无有效 IC 数据' in stdout or '回测未产生结果' in stdout)
    has_result = stdout and '回测完成' in stdout

    if has_no_ic:
        metrics["status"] = "failed"
    elif data.get("return_code") == 0 and (has_result or metrics["ic_mean"] is not None or metrics["total_return"] is not None):
        metrics["status"] = "success"
    elif data.get("status"):
        metrics["status"] = data["status"]
    elif metrics["ic_mean"] is not None or metrics["total_return"] is not None:
        metrics["status"] = "success"
    elif data.get("return_code") == 0:
        metrics["status"] = "success"
    
    return metrics

# ── SQLite入库 ─────────────────────────────────────────────────────

def ensure_table():
    """确保backtest_results表存在（SQLite）"""
    import sqlite3
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS backtest_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_file TEXT,
            timestamp TEXT,
            mode TEXT,
            start_date TEXT,
            end_date TEXT,
            elapsed_seconds REAL,
            ic_mean REAL,
            ic_std REAL,
            ic_positive_pct REAL,
            total_return REAL,
            sharpe_ratio REAL,
            max_drawdown REAL,
            win_rate REAL,
            top_n INTEGER,
            min_score INTEGER,
            status TEXT,
            raw_json TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        )
    """)
    conn.commit()
    cur.close()
    conn.close()
    print(f"[Parser] [OK] SQLite表已就绪: {DB_PATH}")

def insert_result(metrics, raw_data=None):
    """将回测结果写入SQLite"""
    import sqlite3
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    
    # 检查是否已存在(去重)
    cur.execute("SELECT id FROM backtest_results WHERE source_file = ?", (metrics["source_file"],))
    if cur.fetchone():
        print(f"[Parser] [SKIP] 已存在，跳过: {metrics['source_file']}")
        cur.close()
        conn.close()
        return False
    
    cur.execute("""
        INSERT INTO backtest_results 
        (source_file, timestamp, mode, start_date, end_date, elapsed_seconds,
         ic_mean, ic_std, ic_positive_pct, total_return, sharpe_ratio, 
         max_drawdown, win_rate, top_n, min_score, status, raw_json)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        metrics["source_file"], metrics["timestamp"], metrics["mode"],
        metrics["start_date"] or None, metrics["end_date"] or None,
        metrics["elapsed_seconds"], metrics["ic_mean"], metrics["ic_std"],
        metrics["ic_positive_pct"], metrics["total_return"], metrics["sharpe_ratio"],
        metrics["max_drawdown"], metrics["win_rate"], metrics["top_n"],
        metrics["min_score"], metrics["status"],
        json.dumps(raw_data, ensure_ascii=False) if raw_data else None
    ))
    conn.commit()
    cur.close()
    conn.close()
    print(f"[Parser] [OK] 入库成功: IC={metrics['ic_mean']}, 夏普={metrics['sharpe_ratio']}")
    return True

# ── Markdown摘要生成 ──────────────────────────────────────────────

def generate_summary(metrics_list, output_path=None):
    """生成回测结果Markdown摘要"""
    if not output_path:
        output_path = os.path.join(REPORTS_DIR, f"bt_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md")
    
    lines = [
        f"# 回测结果摘要 — {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "",
        f"共解析 **{len(metrics_list)}** 个回测结果",
        "",
        "## 结果总览",
        "",
        "| # | 时间 | 模式 | IC均值 | 夏普 | 最大回撤 | 总收益 | 胜率 | 状态 |",
        "|---|------|------|--------|------|---------|--------|------|------|",
    ]
    
    for i, m in enumerate(metrics_list, 1):
        ts = str(m.get("timestamp", ""))[:19]
        ic = f"{m['ic_mean']:.4f}" if m.get("ic_mean") is not None else "N/A"
        sp = f"{m['sharpe_ratio']:.2f}" if m.get("sharpe_ratio") is not None else "N/A"
        md = f"{m['max_drawdown']:.1f}%" if m.get("max_drawdown") is not None else "N/A"
        tr = f"{m['total_return']:.1f}%" if m.get("total_return") is not None else "N/A"
        wr = f"{m['win_rate']:.1f}%" if m.get("win_rate") is not None else "N/A"
        st = "[OK]" if m.get("status") == "success" else "[FAIL]"
        lines.append(f"| {i} | {ts} | {m.get('mode','?')} | {ic} | {sp} | {md} | {tr} | {wr} | {st} |")
    
    # 统计
    ics = [m["ic_mean"] for m in metrics_list if m.get("ic_mean") is not None]
    sharpes = [m["sharpe_ratio"] for m in metrics_list if m.get("sharpe_ratio") is not None]
    
    lines.extend([
        "",
        "## 统计摘要",
        "",
    ])
    if ics:
        lines.append(f"- **IC均值**: 平均={sum(ics)/len(ics):.4f}, 最大={max(ics):.4f}, 最小={min(ics):.4f}")
    if sharpes:
        lines.append(f"- **夏普比率**: 平均={sum(sharpes)/len(sharpes):.2f}, 最大={max(sharpes):.2f}, 最小={min(sharpes):.2f}")
    
    lines.append(f"\n*由 backtest_result_parser.py 自动生成*")
    
    content = "\n".join(lines)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"[Parser] [DOC] 摘要已生成: {output_path}")
    return output_path

# ── 主流程 ────────────────────────────────────────────────────────

def process_all():
    """处理所有未入库的回测结果"""
    files = find_result_files()
    print(f"[Parser] 找到 {len(files)} 个回测结果文件")
    
    if not files:
        print("[Parser] 无回测结果需要处理")
        return []
    
    # 确保SQLite表存在
    try:
        ensure_table()
    except Exception as e:
        print(f"[Parser] [WARN] 数据库初始化失败: {e}，仅生成摘要")
    
    metrics_list = []
    inserted = 0
    
    for f in files:
        data = load_result(f)
        if not data:
            continue
        metrics = extract_metrics(data, filepath=f)
        metrics_list.append(metrics)
        
        # 尝试入库
        try:
            if insert_result(metrics, data):
                inserted += 1
        except Exception as e:
            print(f"[Parser] [WARN] 入库失败: {e}")
    
    # 生成摘要
    if metrics_list:
        summary_path = generate_summary(metrics_list)
    
    print(f"\n[Parser] 完成: 处理{len(metrics_list)}个, 入库{inserted}个")
    return metrics_list

# ── CLI ────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="回测结果自动解析器")
    parser.add_argument("--file", help="处理单个文件")
    parser.add_argument("--all", action="store_true", help="处理所有结果")
    parser.add_argument("--summary-only", action="store_true", help="仅生成摘要，不入库")
    args = parser.parse_args()
    
    if args.file:
        data = load_result(args.file)
        if data:
            m = extract_metrics(data)
            print(json.dumps(m, indent=2, ensure_ascii=False))
    elif args.all or True:
        process_all()
