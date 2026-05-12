#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
A股季度评分系统 V6.0.0（独立脚本）
功能：季度评分 + 年报A ∩ 季报A 交叉验证选股
"""

import os, sys, json, time, sqlite3, logging, argparse, re, random
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Optional, Tuple
import requests as req_lib

class Config:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    DEFAULT_STOCK_FILE = os.path.join(BASE_DIR, "xuan.txt")
    OUTPUT_DIR = BASE_DIR
    DB_FILE = os.path.join(BASE_DIR, "stock_cache.db")
    PROFIT_W = 0.35; GROWTH_W = 0.30; OCF_W = 0.15; DEBT_W = 0.20
    ROE_SUB_W = 0.40; GROSS_SUB_W = 0.30; NET_SUB_W = 0.30
    REV_YOY_SUB_W = 0.40; PROF_YOY_SUB_W = 0.60
    GRADE_A = 75; GRADE_B = 55; GRADE_C = 40; GRADE_D = 25
    LOW_COMP_PENALTY = 0.9; ULTRA_LOW_COMP_PENALTY = 0.75
    NEG_PROF_PENALTY = 15.0; MARKET_FALLBACK_DISC = 0.95
    MIN_INDUSTRY_SAMPLES = 5
    NEODATA_URL = "https://copilot.tencent.com/agenttool/v1/neodata"
    NEODATA_TOKEN_FILE = os.path.expanduser("~/.workbuddy/.neodata_token")
    API_TIMEOUT = 50; API_RETRY = 2; API_BACKOFF = 3.0
    WORKERS = 8; GLOBAL_TIMEOUT = 7200

logger = logging.getLogger("quarterly")

def load_token():
    with open(Config.NEODATA_TOKEN_FILE, "r", encoding="utf-8") as f:
        token = f.read().strip()
    if not token: raise ValueError("Token 为空")
    return token

def parse_num(text):
    if not text: return None
    m = re.search(r"([-+]?\d+\.?\d*)%", text)
    if m: return float(m.group(1))
    m = re.search(r"([-+]?\d+\.?\d*)", text)
    if m: return float(m.group(1))
    return None

def _extract_quarterly_block(text):
    print(f"DEBUG: Input text length: {len(text)}")
    print(f"First 200 chars: {repr(text[:200])}")

    # 匹配格式：统计截止日期为YYYYMMDD的Q1单季报/Q3单季报
    pattern = r"统计截止日期为(\d{4}(?:0331|0630|0930))的Q[123]单季报"
    matches = list(re.finditer(pattern, text))
    print(f"Pattern matches: {len(matches)}")
    for i, m in enumerate(matches):
        print(f"  Match {i}: '{m.group(0)}', date={m.group(1)}, pos={m.start()}-{m.end()}")

    if not matches:
        # 兜底：匹配任何季度段落（排除年报）
        pattern2 = r"统计截止日期为(\d{4}(?:0331|0630|0930))的(?:单?季报)"
        matches = list(re.finditer(pattern2, text))
        print(f"Pattern2 matches: {len(matches)}")
        for i, m in enumerate(matches):
            print(f"  Match {i}: '{m.group(0)}', date={m.group(1)}, pos={m.start()}-{m.end()}")
        # 过滤掉年报（1231）
        matches = [m for m in matches if m.group(1) != "20251231"]

    if not matches:
        print("No quarterly matches found!")
        return "", ""

    # 取最新的季度（按日期倒序，取第一个）
    latest = sorted(matches, key=lambda x: x.group(1), reverse=True)[0]
    report_date = latest.group(1)
    anchor = "统计截止日期为" + report_date + "的"
    print(f"Anchor: '{anchor}'")
    start = text.find(anchor) + len(anchor)
    print(f"Start at: {start}")
    next_a = text.find("统计截止日期为", start + 1)
    block = text[start:] if next_a == -1 else text[start:next_a]
    print(f"Next anchor at: {next_a}")
    return block.strip(), report_date

def _extract_annual_block(text):
    matches = list(re.finditer(r"统计截止日期为(\d{4})1231的年报", text))
    if not matches: return ""
    last = matches[-1]
    start = text.find(last.group(0))
    if start == -1: return ""
    start += len(last.group(0))
    next_a = text.find("统计截止日期为", start + 1)
    return text[start:] if next_a == -1 else text[start:next_a]

def _extract_metric_line(block, keywords):
    for line in block.split("\n"):
        line = line.strip()
        if not line: continue
        for kw in keywords:
            if kw in line: return line
    return None

def parse_quarterly_finance(block):
    r = {}
    line = _extract_metric_line(block, ["销售毛利率"])
    r["gross_margin"] = parse_num(line[line.find("毛利率"):]) if line and "毛利率" in line else None
    line = _extract_metric_line(block, ["销售净利率"])
    r["net_margin"] = parse_num(line[line.find("净利率"):]) if line and "净利率" in line else None
    line = _extract_metric_line(block, ["营业收入同比增长", "营收同比增长", "营业总收入同比增长"])
    r["revenue_yoy"] = parse_num(line) if line else None
    line = _extract_metric_line(block, ["归母净利润同比增长"])
    r["profit_yoy"] = parse_num(line) if line else None
    return r

def init_db():
    conn = sqlite3.connect(Config.DB_FILE)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=10000")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_reports_ts_type ON financial_reports(ts_code, report_type)")
    conn.commit()
    return conn

def load_annual_from_db(conn, stocks):
    result = []
    for s in stocks:
        ts_code = s["ts_code"]
        cur = conn.execute(
            "SELECT * FROM financial_reports WHERE ts_code=? AND report_type='annual' AND fetch_success=1 ORDER BY report_date DESC LIMIT 1",
            (ts_code,))
        row = cur.fetchone()
        cur2 = conn.execute("SELECT industry_l1 FROM stocks WHERE ts_code=?", (ts_code,))
        sr = cur2.fetchone()
        item = {"ts_code": ts_code, "name": s.get("name", ""), "industry_l1": sr[0] if sr else "", "fetch_success": False}
        if row:
            cols = [d[0] for d in cur.description]
            report = dict(zip(cols, row))
            item.update({"roe": report.get("roe"), "gross_margin": report.get("gross_margin"),
                         "net_margin": report.get("net_margin"), "revenue_yoy": report.get("revenue_yoy"),
                         "profit_yoy": report.get("profit_yoy"), "debt_ratio": report.get("debt_ratio"),
                         "net_profit": report.get("net_profit"), "deducted_profit": report.get("deducted_profit"),
                         "revenue": report.get("revenue"), "ocf_to_profit": report.get("ocf_to_profit"),
                         "ocf_abs": report.get("ocf_abs"), "asset_turnover": report.get("asset_turnover"),
                         "ar_turnover": report.get("ar_turnover"), "fetch_success": bool(report.get("fetch_success")),
                         "annual_report_date": report.get("report_date")})
        else:
            for f in ["roe","gross_margin","net_margin","revenue_yoy","profit_yoy","debt_ratio",
                       "net_profit","deducted_profit","revenue","ocf_to_profit","ocf_abs",
                       "asset_turnover","ar_turnover"]:
                item[f] = None
            item["annual_report_date"] = None
        result.append(item)
    return result

def save_quarterly(conn, ts_code, report_date, metrics, success):
    now_str = datetime.now().isoformat()
    conn.execute(
        "INSERT OR REPLACE INTO financial_reports "
        "(ts_code,report_date,report_type,roe,gross_margin,net_margin,revenue_yoy,profit_yoy,"
        "debt_ratio,net_profit,deducted_profit,revenue,ocf_to_profit,ocf_abs,asset_turnover,ar_turnover,"
        "fetch_success,last_update) VALUES (?,?,'quarterly',?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (ts_code, report_date, metrics.get("roe"), metrics.get("gross_margin"), metrics.get("net_margin"),
         metrics.get("revenue_yoy"), metrics.get("profit_yoy"), metrics.get("debt_ratio"),
         metrics.get("net_profit"), metrics.get("deducted_profit"), metrics.get("revenue"),
         metrics.get("ocf_to_profit"), metrics.get("ocf_abs"), metrics.get("asset_turnover"),
         metrics.get("ar_turnover"), 1 if success else 0, now_str))
    conn.commit()

def has_quarterly_cache(conn, ts_code):
    cur = conn.execute("SELECT 1 FROM financial_reports WHERE ts_code=? AND report_type='quarterly' AND fetch_success=1 LIMIT 1", (ts_code,))
    return cur.fetchone() is not None

def run_neodata(query, token):
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    for attempt in range(1, Config.API_RETRY + 2):
        try:
            resp = req_lib.post(Config.NEODATA_URL, json={"query": query}, headers=headers, timeout=Config.API_TIMEOUT)
            resp.raise_for_status()
            data = resp.json()
            if isinstance(data.get("data"), dict): return data["data"].get("text", "")
            if isinstance(data.get("data"), str): return data["data"]
            return json.dumps(data, ensure_ascii=False)
        except Exception as e:
            logger.warning(f"API 错误 (attempt {attempt}): {e}")
            if attempt < Config.API_RETRY + 1: time.sleep(Config.API_BACKOFF ** attempt)
    return ""

def fetch_quarterly(ts_code, name, token):
    query = f"{ts_code} {name} 年报"
    try:
        text = run_neodata(query, token)
        if not text: return {"metrics": {}, "report_date": "", "fetch_success": False}
        q_block, q_date = _extract_quarterly_block(text)
        if not q_block: return {"metrics": {}, "report_date": "", "fetch_success": False}
        metrics = parse_quarterly_finance(q_block)
        return {"metrics": metrics, "report_date": q_date, "fetch_success": True}
    except Exception as e:
        logger.error(f"季度获取异常 {ts_code}: {e}")
        return {"metrics": {}, "report_date": "", "fetch_success": False}

def fetch_quarterly_batch(stocks, token, force_refresh=False, conn=None):
    total = len(stocks)
    results = []
    api_errors = 0
    start_time = time.time()
    adapter = HTTPAdapter(pool_connections=Config.WORKERS, pool_maxsize=Config.WORKERS, max_retries=2)
    session = req_lib.Session()
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    logger.info(f"开始获取季度数据: 共 {total} 只, {Config.WORKERS} 线程")

    with ThreadPoolExecutor(max_workers=Config.WORKERS) as executor:
        futures = {}
        for s in stocks:
            if not force_refresh and conn and has_quarterly_cache(conn, s["ts_code"]):
                continue
            futures[executor.submit(fetch_quarterly, s["ts_code"], s["name"], token)] = s
        done_count = 0
        for future in as_completed(futures):
            s = futures[future]
            done_count += 1
            try:
                result = future.result(timeout=Config.API_TIMEOUT + 10)
                results.append({**s, **result})
                if not result.get("fetch_success"): api_errors += 1
            except Exception as e:
                api_errors += 1
                results.append({**s, "metrics": {}, "report_date": "", "fetch_success": False})
                logger.error(f"季度任务异常 {s['ts_code']}: {e}")
            if done_count % 50 == 0:
                elapsed = time.time() - start_time
                logger.info(f"季度进度: {done_count}, 速率:{done_count/elapsed:.1f}/s, 已用:{elapsed:.0f}s, 错误:{api_errors}")

    session.close()
    logger.info(f"季度获取完成: {len(results)} 只, 错误:{api_errors}, 耗时:{time.time()-start_time:.0f}s")
    return results

CORE_METRICS = ["roe", "gross_margin", "net_margin", "revenue_yoy", "profit_yoy", "ocf_to_profit", "debt_ratio"]

def calc_completeness(metrics):
    non_null = sum(1 for m in CORE_METRICS if metrics.get(m) is not None)
    ratio = non_null / len(CORE_METRICS)
    if ratio >= 0.7: return ratio, "high"
    if ratio >= 0.4: return ratio, "medium"
    if non_null <= 1: return ratio, "ultra_low"
    return ratio, "low"

def percentile_rank(value, values, reverse=False):
    if not values: return 50.0
    sorted_vals = sorted(values, reverse=reverse)
    n = len(sorted_vals)
    for i, v in enumerate(sorted_vals):
        if value >= v: return (i / (n - 1)) * 100 if n > 1 else 50.0
    return 0.0

def calc_quarterly_score(annual_data, quarterly_metrics, industry_groups, all_stocks):
    ts_code = annual_data.get("ts_code", "")
    name = annual_data.get("name", "")
    industry = annual_data.get("industry_l1", "")

    merged = dict(annual_data)
    for k, v in quarterly_metrics.items():
        if v is not None: merged[k] = v

    m = {"roe": merged.get("roe"), "gross_margin": merged.get("gross_margin"),
         "net_margin": merged.get("net_margin"), "revenue_yoy": merged.get("revenue_yoy"),
         "profit_yoy": merged.get("profit_yoy"), "debt_ratio": merged.get("debt_ratio"),
         "ocf_to_profit": merged.get("ocf_to_profit"), "net_profit": merged.get("net_profit"),
         "ocf_abs": merged.get("ocf_abs")}

    pool = industry_groups.get(industry, [])
    use_fallback = len(pool) < Config.MIN_INDUSTRY_SAMPLES
    if use_fallback: pool = all_stocks
    discount = Config.MARKET_FALLBACK_DISC if use_fallback else 1.0

    def pv(key): return [s[key] for s in pool if s.get(key) is not None]

    roe_s = 0.0 if m["roe"] is None else (0.0 if m["roe"] < 0 else percentile_rank(m["roe"], pv("roe")))
    gross_s = percentile_rank(m["gross_margin"], pv("gross_margin")) if m["gross_margin"] is not None else 0.0
    net_s = percentile_rank(m["net_margin"], pv("net_margin")) if m["net_margin"] is not None else 0.0
    profit_score = (roe_s * Config.ROE_SUB_W + gross_s * Config.GROSS_SUB_W + net_s * Config.NET_SUB_W) * discount

    rev_s = percentile_rank(m["revenue_yoy"], pv("revenue_yoy")) if m["revenue_yoy"] is not None else 0.0
    prof_s = percentile_rank(m["profit_yoy"], pv("profit_yoy")) if m["profit_yoy"] is not None else 0.0
    growth_score = (rev_s * Config.REV_YOY_SUB_W + prof_s * Config.PROF_YOY_SUB_W) * discount

    ocf_s = percentile_rank(m["ocf_to_profit"], pv("ocf_to_profit")) if m["ocf_to_profit"] is not None else 0.0
    ocf_s *= discount

    debt_s = percentile_rank(m["debt_ratio"], pv("debt_ratio"), reverse=True) if m["debt_ratio"] is not None else 0.0
    debt_s *= discount

    total = profit_score * Config.PROFIT_W + growth_score * Config.GROWTH_W + ocf_s * Config.OCF_W + debt_s * Config.DEBT_W

    completeness, level = calc_completeness(m)
    if level == "low": total *= Config.LOW_COMP_PENALTY
    elif level == "ultra_low": total *= Config.LOW_COMP_PENALTY * Config.ULTRA_LOW_COMP_PENALTY

    if m["net_profit"] is not None and m["net_profit"] < 0 and m["ocf_abs"] is not None and m["ocf_abs"] < 0:
        total = min(total, Config.NEG_PROF_PENALTY)

    if total >= Config.GRADE_A: grade = "A"
    elif total >= Config.GRADE_B: grade = "B"
    elif total >= Config.GRADE_C: grade = "C"
    elif total >= Config.GRADE_D: grade = "D"
    else: grade = "E"

    confidence = {"high": "高", "medium": "中", "low": "低", "ultra_low": "低"}[level]

    return {
        "ts_code": ts_code, "name": name, "industry_l1": industry,
        "total_score": round(total, 2), "profit_score": round(profit_score, 2),
        "growth_score": round(growth_score, 2), "ocf_score": round(ocf_s, 2),
        "debt_score": round(debt_s, 2), "grade": grade, "confidence": confidence,
        "completeness": completeness, "completeness_level": level,
        "data_source": "季报+年报补充",
        "q_gross_margin": quarterly_metrics.get("gross_margin"),
        "q_net_margin": quarterly_metrics.get("net_margin"),
        "q_revenue_yoy": quarterly_metrics.get("revenue_yoy"),
        "q_profit_yoy": quarterly_metrics.get("profit_yoy"),
        "a_roe": m["roe"], "a_debt_ratio": m["debt_ratio"], "a_ocf_to_profit": m["ocf_to_profit"],
        "annual_roe": annual_data.get("roe"), "annual_gross_margin": annual_data.get("gross_margin"),
        "annual_net_margin": annual_data.get("net_margin"), "annual_revenue_yoy": annual_data.get("revenue_yoy"),
        "annual_profit_yoy": annual_data.get("profit_yoy"), "annual_debt_ratio": annual_data.get("debt_ratio"),
        "annual_ocf_to_profit": annual_data.get("ocf_to_profit"),
        "annual_report_date": annual_data.get("annual_report_date"),
        "quarterly_report_date": quarterly_metrics.get("_report_date", ""),
        "fetch_success": True, "market_fallback": use_fallback,
    }

def calc_annual_score(stock, industry_groups, all_stocks):
    ts_code = stock.get("ts_code", "")
    industry = stock.get("industry_l1", "")
    m = {"roe": stock.get("roe"), "gross_margin": stock.get("gross_margin"),
         "net_margin": stock.get("net_margin"), "revenue_yoy": stock.get("revenue_yoy"),
         "profit_yoy": stock.get("profit_yoy"), "debt_ratio": stock.get("debt_ratio"),
         "ocf_to_profit": stock.get("ocf_to_profit"), "net_profit": stock.get("net_profit"),
         "ocf_abs": stock.get("ocf_abs")}

    pool = industry_groups.get(industry, [])
    use_fallback = len(pool) < Config.MIN_INDUSTRY_SAMPLES
    if use_fallback: pool = all_stocks
    discount = Config.MARKET_FALLBACK_DISC if use_fallback else 1.0

    def pv(key): return [s[key] for s in pool if s.get(key) is not None]

    roe_s = 0.0 if m["roe"] is None else (0.0 if m["roe"] < 0 else percentile_rank(m["roe"], pv("roe")))
    gross_s = percentile_rank(m["gross_margin"], pv("gross_margin")) if m["gross_margin"] is not None else 0.0
    net_s = percentile_rank(m["net_margin"], pv("net_margin")) if m["net_margin"] is not None else 0.0
    profit_score = (roe_s * Config.ROE_SUB_W + gross_s * Config.GROSS_SUB_W + net_s * Config.NET_SUB_W) * discount

    rev_s = percentile_rank(m["revenue_yoy"], pv("revenue_yoy")) if m["revenue_yoy"] is not None else 0.0
    prof_s = percentile_rank(m["profit_yoy"], pv("profit_yoy")) if m["profit_yoy"] is not None else 0.0
    growth_score = (rev_s * Config.REV_YOY_SUB_W + prof_s * Config.PROF_YOY_SUB_W) * discount

    ocf_s = percentile_rank(m["ocf_to_profit"], pv("ocf_to_profit")) if m["ocf_to_profit"] is not None else 0.0
    ocf_s *= discount

    debt_s = percentile_rank(m["debt_ratio"], pv("debt_ratio"), reverse=True) if m["debt_ratio"] is not None else 0.0
    debt_s *= discount

    total = profit_score * Config.PROFIT_W + growth_score * Config.GROWTH_W + ocf_s * Config.OCF_W + debt_s * Config.DEBT_W

    completeness, level = calc_completeness(m)
    if level == "low": total *= Config.LOW_COMP_PENALTY
    elif level == "ultra_low": total *= Config.LOW_COMP_PENALTY * Config.ULTRA_LOW_COMP_PENALTY

    if m["net_profit"] is not None and m["net_profit"] < 0 and m["ocf_abs"] is not None and m["ocf_abs"] < 0:
        total = min(total, Config.NEG_PROF_PENALTY)

    if total >= Config.GRADE_A: grade = "A"
    elif total >= Config.GRADE_B: grade = "B"
    elif total >= Config.GRADE_C: grade = "C"
    elif total >= Config.GRADE_D: grade = "D"
    else: grade = "E"

    confidence = {"high": "高", "medium": "中", "low": "低", "ultra_low": "低"}[level]

    return {
        "ts_code": ts_code, "name": stock.get("name", ""), "industry_l1": industry,
        "total_score": round(total, 2), "profit_score": round(profit_score, 2),
        "growth_score": round(growth_score, 2), "ocf_score": round(ocf_s, 2),
        "debt_score": round(debt_s, 2), "grade": grade, "confidence": confidence,
        "completeness": completeness, "completeness_level": level,
        "roe": m["roe"], "gross_margin": m["gross_margin"], "net_margin": m["net_margin"],
        "revenue_yoy": m["revenue_yoy"], "profit_yoy": m["profit_yoy"],
        "debt_ratio": m["debt_ratio"], "ocf_to_profit": m["ocf_to_profit"],
        "net_profit": m["net_profit"], "ocf_abs": m["ocf_abs"],
        "annual_report_date": stock.get("annual_report_date"),
        "fetch_success": stock.get("fetch_success", False),
        "market_fallback": use_fallback, "data_source": "年报",
    }

def load_stock_list(file_path=Config.DEFAULT_STOCK_FILE):
    stocks = []
    with open(file_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line: continue
            parts = line.split()
            if len(parts) < 2: parts = line.split(",")
            if len(parts) < 2: parts = line.split("\t")
            if len(parts) < 2: continue
            code, name = parts[0].strip(), parts[1].strip()
            if code.startswith(("688", "430", "83", "87")): continue
            if "." not in code: code = code + ".SH" if code.startswith("6") else code + ".SZ"
            stocks.append({"ts_code": code, "name": name})
    return stocks

MOCK_RESPONSE = """
统计截止日期为20260331的Q1单季报
销售毛利率45.23%
销售净利率22.15%
归母净利润同比增长18.67%

统计截止日期为20251231的年报
加权净资产收益率ROE18.52%
销售毛利率43.21%
销售净利率20.88%
营业收入同比增长25.30%
归母净利润同比增长32.15%
资产负债率35.60%
营业总收入12500000000.00元
净利润2560000000.00元
扣非净利润2380000000.00元
经营活动产生的现金流量净额2890000000.00元
净利润现金含量112.89%
总资产周转率0.92次
应收账款周转率7.45次

统计截止日期为20250930的Q3单季报
销售毛利率44.10%
销售净利率21.50%
营业收入同比增长22.80%
归母净利润同比增长28.90%
"""

def run_self_test():
    logger.info("=" * 60)
    logger.info("季度评分系统自测")
    logger.info("=" * 60)
    passed = failed = 0

    print(f"DEBUG: MOCK_RESPONSE length: {len(MOCK_RESPONSE)}")
    print(f"First 300 chars: {repr(MOCK_RESPONSE[:300])}")

    q_block, q_date = _extract_quarterly_block(MOCK_RESPONSE)
    if q_block and "Q1单季报" not in q_block and "45.23" in q_block:
        logger.info("[PASS] 季度段落提取正确"); passed += 1
    else:
        logger.error(f"[FAIL] 季度段落提取: {q_block[:80]}"); failed += 1

    if q_date == "20260331":
        logger.info(f"[PASS] 季度日期: {q_date}"); passed += 1
    else:
        logger.error(f"[FAIL] 季度日期: {q_date}"); failed += 1

    qm = parse_quarterly_finance(q_block)
    for key, exp in [("gross_margin", 45.23), ("net_margin", 22.15), ("profit_yoy", 18.67)]:
        act = qm.get(key)
        if act is not None and abs(act - exp) < 0.01:
            logger.info(f"[PASS] {key}: {act}"); passed += 1
        else:
            logger.error(f"[FAIL] {key}: 期望 {exp}, 实际 {act}"); failed += 1

    if qm.get("revenue_yoy") is None:
        logger.info("[PASS] Q1 营收同比为 None（符合预期）"); passed += 1
    else:
        logger.info(f"[INFO] Q1 营收同比: {qm['revenue_yoy']}"); passed += 1

    ab = _extract_annual_block(MOCK_RESPONSE)
    if ab and "ROE18.52" in ab:
        logger.info("[PASS] 年报段落提取正确"); passed += 1
    else:
        logger.error("[FAIL] 年报段落提取"); failed += 1

    if "ROE" not in q_block and "资产负债率" not in q_block:
        logger.info("[PASS] 季度段落不含年报独有字段"); passed += 1
    else:
        logger.error("[FAIL] 季度段落混入年报字段"); failed += 1

    logger.info(f"自测完成: {passed} 通过, {failed} 失败")
    return failed == 0

def main():
    parser = argparse.ArgumentParser(description="A股季度评分系统 V6.0.0")
    parser.add_argument("--test", action="store_true", help="运行自测并退出")
    parser.add_argument("--verify", type=int, default=0, help="随机取N只股票端到端验证")
    parser.add_argument("--force", action="store_true", help="强制刷新季度数据")
    args = parser.parse_args()

    if args.test:
        ok = run_self_test()
        sys.exit(0 if ok else 1)

    # 加载 token
    try:
        token = load_token()
    except Exception as e:
        logger.error(f"加载 Token 失败: {e}")
        sys.exit(1)

    # 加载股票列表
    stocks = load_stock_list()
    if not stocks:
        logger.error("股票列表为空")
        sys.exit(1)

    # 初始化数据库
    conn = init_db()

    # 加载年报数据
    annual_data = load_annual_from_db(conn, stocks)
    logger.info(f"从缓存加载年报数据: {len(annual_data)} 只")

    # 按行业分组（用于评分）
    industry_groups = {}
    for s in annual_data:
        ind = s.get("industry_l1", "未知")
        if ind not in industry_groups:
            industry_groups[ind] = []
        industry_groups[ind].append(s)
    all_stocks = annual_data

    # 计算年报评分
    logger.info("计算年报评分...")
    annual_scored = []
    for s in annual_data:
        score = calc_annual_score(s, industry_groups, all_stocks)
        annual_scored.append(score)

    # 获取季度数据
    logger.info("获取季度数据...")
    quarterly_raw = fetch_quarterly_batch(annual_data, token, force_refresh=args.force, conn=conn)

    # 保存季度数据到数据库
    for r in quarterly_raw:
        ts_code = r["ts_code"]
        report_date = r.get("report_date", "")
        metrics = r.get("metrics", {})
        success = r.get("fetch_success", False)
        save_quarterly(conn, ts_code, report_date, metrics, success)

    # 合并季度评分
    logger.info("计算季度评分...")
    quarterly_scored = []
    for a in annual_data:
        ts_code = a["ts_code"]
        q = next((r for r in quarterly_raw if r["ts_code"] == ts_code), None)
        if q and q.get("fetch_success"):
            score = calc_quarterly_score(a, q["metrics"], industry_groups, all_stocks)
            score["quarterly_total_score"] = score["total_score"]
            score["quarterly_grade"] = score["grade"]
            quarterly_scored.append(score)
        else:
            # 季度数据失败，复制年报评分但标记
            s = calc_annual_score(a, industry_groups, all_stocks)
            s["data_source"] = "年报（无季度）"
            s["quarterly_total_score"] = None
            s["quarterly_grade"] = None
            quarterly_scored.append(s)

    # 交集计算
    annual_a_codes = {r["ts_code"] for r in annual_scored if r.get("grade") == "A"}
    quarterly_a_codes = {r["ts_code"] for r in quarterly_scored if r.get("quarterly_grade") == "A"}
    preferred_codes = annual_a_codes & quarterly_a_codes
    preferred = [r for r in quarterly_scored if r["ts_code"] in preferred_codes]
    annual_only_a = [r for r in annual_scored if r.get("grade") == "A" and r["ts_code"] not in preferred_codes]
    quarterly_only_a = [r for r in quarterly_scored if r.get("quarterly_grade") == "A" and r["ts_code"] not in preferred_codes]

    logger.info(f"年报A级: {len(annual_a_codes)} 只")
    logger.info(f"季报A级: {len(quarterly_a_codes)} 只")
    logger.info(f"★ 交集优选: {len(preferred_codes)} 只 ★")

    # 输出 JSON 报告
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    json_path = os.path.join(Config.OUTPUT_DIR, f"季报年报交叉验证_{timestamp}.json")
    output = {
        "data_timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "total_stocks": len(stocks),
        "annual_a_count": len(annual_a_codes),
        "quarterly_a_count": len(quarterly_a_codes),
        "preferred_count": len(preferred_codes),
        "preferred_stocks": [
            {"ts_code": r["ts_code"], "name": r["name"], "industry_l1": r["industry_l1"],
             "annual_score": r.get("total_score"), "annual_grade": r.get("grade"),
             "quarterly_score": r.get("quarterly_total_score"), "quarterly_grade": r.get("quarterly_grade")}
            for r in preferred
        ],
        "annual_only_a": [
            {"ts_code": r["ts_code"], "name": r["name"], "score": r.get("total_score"), "grade": r.get("grade")}
            for r in annual_only_a
        ],
        "quarterly_only_a": [
            {"ts_code": r["ts_code"], "name": r["name"], "score": r.get("quarterly_total_score"), "grade": r.get("quarterly_grade")}
            for r in quarterly_only_a
        ]
    }
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    logger.info(f"JSON 报告已保存: {json_path}")

    # 随机验证（如果需要）
    if args.verify > 0:
        sample_codes = random.sample(list(stocks), min(args.verify, len(stocks)))
        logger.info(f"随机验证 {args.verify} 只股票...")
        for code in sample_codes:
            a = next((r for r in annual_scored if r["ts_code"] == code), None)
            q = next((r for r in quarterly_scored if r["ts_code"] == code), None)
            if a and q:
                logger.info(f"{code}: 年报评分={a.get('total_score','N/A')}({a.get('grade','N/A')}), "
                           f"季报评分={q.get('quarterly_total_score','N/A')}({q.get('quarterly_grade','N/A')})")

    conn.close()
    logger.info("=" * 60)
    logger.info("季度评分系统完成！")
    logger.info(f"★ 年报A∩季报A = {len(preferred_codes)} 只优选股票 ★")
    logger.info("=" * 60)

if __name__ == "__main__":
    main()