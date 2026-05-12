#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
A股智能选股系统 V5.0.0
基于 NeoData 真实 API 数据，对 A 股年报进行结构化段落匹配与业绩评分。
"""

import os, sys, json, time, sqlite3, logging, argparse, re
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Optional
import requests as req_lib
from requests.adapters import HTTPAdapter

# ============================================================
# 配置
# ============================================================
class Config:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    DEFAULT_STOCK_FILE = os.path.join(BASE_DIR, "xuan.txt")
    OUTPUT_DIR = BASE_DIR
    INDUSTRY_MAP_FILE = os.path.join(BASE_DIR, "industry_map.json")
    DB_FILE = os.path.join(BASE_DIR, "stock_cache.db")
    FINANCE_WORKERS = 16
    API_RETRY_TIMES = 2
    API_RETRY_BACKOFF_BASE = 3.0
    API_TIMEOUT = 50
    PAUSE_CONSECUTIVE_EMPTY = 10
    PAUSE_DURATION = 20
    GLOBAL_TIMEOUT = 7200
    MIN_INDUSTRY_SAMPLES = 5
    CACHE_MAX_AGE_ANNUAL = 400
    NEGATIVE_PROFIT_PENALTY = 15.0
    MARKET_FALLBACK_DISCOUNT = 0.95
    LOW_COMPLETENESS_PENALTY = 0.9
    ULTRA_LOW_COMPLETENESS_PENALTY = 0.75
    INDUSTRY_API_WORKERS = 15
    INDUSTRY_CACHE_DAYS = 365
    ANNUAL_DISCLOSURE_DEADLINE_MONTH = 4
    ANNUAL_DISCLOSURE_DEADLINE_DAY = 30
    NEODATA_URL = "https://copilot.tencent.com/agenttool/v1/neodata"
    NEODATA_TOKEN_FILE = os.path.expanduser("~/.workbuddy/.neodata_token")

# ============================================================
# 日志
# ============================================================
def setup_logging():
    log_file = os.path.join(Config.BASE_DIR, "stock_analyzer.log")
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.FileHandler(log_file, encoding="utf-8", mode="a"),
            logging.StreamHandler(sys.stdout),
        ],
    )
    return logging.getLogger(__name__)

logger = setup_logging()

# ============================================================
# 工具函数
# ============================================================
def load_token() -> str:
    if not os.path.exists(Config.NEODATA_TOKEN_FILE):
        raise FileNotFoundError(f"NeoData Token 文件不存在: {Config.NEODATA_TOKEN_FILE}")
    with open(Config.NEODATA_TOKEN_FILE, "r", encoding="utf-8") as f:
        token = f.read().strip()
    if not token:
        raise ValueError("NeoData Token 文件为空")
    return token

def parse_num(text: str) -> Optional[float]:
    if not text:
        return None
    text = text.strip()
    m = re.search(r"([-+]?\d+\.?\d*)%", text)
    if m:
        return float(m.group(1))
    m = re.search(r"([-+]?\d+\.?\d*)", text)
    if m:
        return float(m.group(1))
    return None

def _parse_num_from_line(line: str) -> Optional[float]:
    """从财报行提取带单位数值，单位匹配顺序：万亿元>亿元>万元>千元>元"""
    m = re.search(r'([-+]?\d+\.?\d*)\s*(万亿元|亿元|万元|千元|元)', line)
    if not m:
        return None
    val = float(m.group(1))
    unit = m.group(2)
    if unit == "万亿元": return val * 1e12
    elif unit == "亿元": return val * 1e8
    elif unit == "万元": return val * 1e4
    elif unit == "千元": return val * 1e3
    else: return val

def year_of_date(date_str: str) -> int:
    return int(str(date_str)[:4])

# ============================================================
# 自测数据
# ============================================================
MOCK_NEODATA_RESPONSE = """
统计截止日期为20230331的季报
营业收入4182651234.56元
归母净利润同比增长12.34%

统计截止日期为20241231的年报
加权净资产收益率ROE15.67%
销售毛利率42.35%
销售净利率18.22%
营业收入同比增长28.45%
归母净利润同比增长35.67%
资产负债率38.92%
营业总收入18654321098.76元
净利润1642130865.33元
扣非净利润1523456789.01元
经营活动产生的现金流量净额2156789012.34元
净利润现金含量160.44%
净利润增长率25.80%
总资产周转率0.85次
应收账款周转率6.78次
经营现金流/净利润145.67%

统计截止日期为20240930的季报
营业收入1234567890.12元
归母净利润同比增长15.67%
"""

# ============================================================
# 年报解析（V5 核心：直接段落匹配）
# ============================================================
def _extract_annual_block(text: str, year: Optional[int] = None) -> str:
    """精确提取年报段落，锚点：统计截止日期为YYYY1231的年报"""
    if year:
        target = f"统计截止日期为{year}1231的年报"
    else:
        matches = list(re.finditer(r"统计截止日期为(\d{4})1231的年报", text))
        if not matches:
            return ""
        last = matches[-1]
        target = last.group(0)
    start = text.find(target)
    if start == -1:
        return ""
    start += len(target)
    next_anchor = text.find("统计截止日期为", start + 1)
    if next_anchor == -1:
        block = text[start:]
    else:
        block = text[start:next_anchor]
    return block.strip()

def _guess_date_from_trend(text: str) -> Dict:
    return {}

def _extract_metric_line(block: str, keywords: List[str]) -> Optional[str]:
    """在年报段落内按关键词逐行搜索"""
    for line in block.split("\n"):
        line = line.strip()
        if not line:
            continue
        for kw in keywords:
            if kw in line:
                return line
    return None

def parse_financial_all(block: str) -> Dict:
    """从年报段落提取 13 个财务指标"""
    result = {}
    # 盈利能力
    line = _extract_metric_line(block, ["加权净资产收益率ROE", "净资产收益率ROE", "加权净资产收益率"])
    result["roe"] = parse_num(line) if line else None
    line = _extract_metric_line(block, ["销售毛利率"])
    result["gross_margin"] = parse_num(line[line.find("毛利率"):]) if line and "毛利率" in line else None
    line = _extract_metric_line(block, ["销售净利率"])
    result["net_margin"] = parse_num(line[line.find("净利率"):]) if line and "净利率" in line else None
    # 成长性
    line = _extract_metric_line(block, ["营业收入同比增长", "营收同比增长", "营业总收入同比增长"])
    result["revenue_yoy"] = parse_num(line) if line else None
    line = _extract_metric_line(block, ["归母净利润同比增长"])
    result["profit_yoy"] = parse_num(line) if line else None
    # 偿债风险
    line = _extract_metric_line(block, ["资产负债率"])
    result["debt_ratio"] = parse_num(line) if line else None
    # 规模与现金流
    line = _extract_metric_line(block, ["营业总收入", "营业收入"])
    result["revenue"] = _parse_num_from_line(line) if line else None
    # 净利润（特殊逻辑：不含归母/扣非/现金含量/增长率/同比）
    result["net_profit"] = None
    for l in block.split("\n"):
        l = l.strip()
        if l.startswith("净利润") and all(x not in l for x in ["归母","扣非","现金含量","增长率","同比"]):
            result["net_profit"] = _parse_num_from_line(l)
            break
    line = _extract_metric_line(block, ["扣非净利润"])
    result["deducted_profit"] = _parse_num_from_line(line) if line else None
    line = _extract_metric_line(block, ["经营活动产生的现金流量净额"])
    result["ocf_abs"] = _parse_num_from_line(line) if line else None
    # 经营现金流/净利润（计算值）
    if result.get("net_profit") and result.get("ocf_abs") and result["net_profit"] != 0:
        result["ocf_to_profit"] = round(result["ocf_abs"] / result["net_profit"] * 100, 2)
    else:
        result["ocf_to_profit"] = None
    # 运营效率
    line = _extract_metric_line(block, ["总资产周转率"])
    result["asset_turnover"] = parse_num(line) if line else None
    line = _extract_metric_line(block, ["应收账款周转率"])
    result["ar_turnover"] = parse_num(line) if line else None
    return result

# ============================================================
# 行业归属确定
# ============================================================
_FALLBACK_INDUSTRY_MAP: Dict[str, str] = {}
SECONDARY_TO_PRIMARY: Dict[str, str] = {}
NAME_KEYWORD_INDUSTRY: Dict[str, str] = {
    "银行":"银行","证券":"非银金融","保险":"非银金融","地产":"房地产","房地产":"房地产",
    "钢铁":"钢铁","煤炭":"煤炭","有色":"有色金属","化工":"基础化工","医药":"医药生物",
    "生物":"医药生物","电子":"电子","计算机":"计算机","通信":"通信","汽车":"汽车",
    "机械":"机械设备","电力":"公用事业","食品":"食品饮料","饮料":"食品饮料","家电":"家用电器",
    "纺织":"纺织服饰","建筑":"建筑装饰","军工":"国防军工","传媒":"传媒","光伏":"电力设备",
    "电池":"电力设备","半导体":"电子","芯片":"电子",
}
CODE_PREFIX_INDUSTRY: Dict[str, str] = {"60":"银行","00":"房地产","30":"医药生物","68":"电子"}

def load_industry_map() -> Dict:
    if os.path.exists(Config.INDUSTRY_MAP_FILE):
        with open(Config.INDUSTRY_MAP_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def extract_industry_from_content(text: str) -> Optional[str]:
    for p in [r"所属一级行业[：:]\s*(\S+)", r"申万一级行业[：:]\s*(\S+)", r"行业分类[：:]\s*(\S+)"]:
        m = re.search(p, text)
        if m:
            return m.group(1).strip()
    return None

def infer_industry_from_name(name: str) -> Optional[str]:
    for kw, industry in NAME_KEYWORD_INDUSTRY.items():
        if kw in name:
            return industry
    return None

def determine_industry(ts_code, name, content, industry_map, use_api=True, session=None) -> Optional[str]:
    """多级策略确定申万一级行业：文本解析→本地映射→二级转一级→名称规则→API补调→代码前缀"""
    ind = extract_industry_from_content(content)
    if ind: return ind
    code_short = ts_code.split(".")[0]
    if ts_code in industry_map: return industry_map[ts_code].get("industry_l1")
    if code_short in industry_map: return industry_map[code_short].get("industry_l1")
    ind = infer_industry_from_name(name)
    if ind: return ind
    if use_api:
        ind = fetch_industry_by_api(ts_code, name, session)
        if ind: return ind
    prefix = code_short[:2]
    return CODE_PREFIX_INDUSTRY.get(prefix)

def fetch_industry_by_api(ts_code, name, session=None) -> Optional[str]:
    token = load_token()
    query = f"{ts_code} {name} 所属行业"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    try:
        if session:
            resp = session.post(Config.NEODATA_URL, json={"query": query}, headers=headers, timeout=30)
        else:
            resp = req_lib.post(Config.NEODATA_URL, json={"query": query}, headers=headers, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        text = data.get("data", {}).get("text", "") if isinstance(data.get("data"), dict) else str(data)
        return extract_industry_from_content(text)
    except Exception as e:
        logger.debug(f"行业API查询失败 {ts_code}: {e}")
        return None

def batch_industry_patch(stocks: List[Dict], industry_map: Dict, workers=Config.INDUSTRY_API_WORKERS):
    """批量 API 补调行业，每批 100 只，批间休眠 1s，15线程+Session连接池"""
    BATCH_SIZE = 100
    need_patch = [s for s in stocks if not s.get("industry_l1")]
    total = len(need_patch)
    if total == 0: return
    logger.info(f"行业补调: 共 {total} 只股票需要补调")
    adapter = HTTPAdapter(pool_connections=workers, pool_maxsize=workers, max_retries=1)
    session = req_lib.Session()
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    api_errors = 0
    results = []
    for batch_start in range(0, total, BATCH_SIZE):
        batch = need_patch[batch_start:batch_start+BATCH_SIZE]
        batch_num = batch_start // BATCH_SIZE + 1
        total_batches = (total + BATCH_SIZE - 1) // BATCH_SIZE
        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures = {executor.submit(determine_industry, s["ts_code"], s["name"], s.get("content",""), industry_map, True, session): s for s in batch}
            for future in as_completed(futures):
                s = futures[future]
                try:
                    ind = future.result(timeout=60)
                    if ind:
                        s["industry_l1"] = ind
                        results.append((s["ts_code"], ind))
                except Exception as e:
                    api_errors += 1
                    logger.debug(f"行业补调失败 {s['ts_code']}: {e}")
        done = min(batch_start + BATCH_SIZE, total)
        logger.info(f"行业补调批次 {batch_num}/{total_batches}: {done}/{total}, 成功{len(results)}, API错误{api_errors}")
        if batch_start + BATCH_SIZE < total:
            time.sleep(1)
    session.close()
    logger.info(f"行业补调完成: 成功 {len(results)}/{total}")

# ============================================================
# 数据库（SQLite 缓存）
# ============================================================
def init_db(db_path=Config.DB_FILE):
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=10000")
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS stocks (
            ts_code TEXT PRIMARY KEY, name TEXT, industry_l1 TEXT, industry_l2 TEXT,
            last_industry_update TEXT, last_full_update TEXT
        );
        CREATE TABLE IF NOT EXISTS financial_reports (
            ts_code TEXT, report_date TEXT, report_type TEXT DEFAULT 'annual',
            roe REAL, gross_margin REAL, net_margin REAL, revenue_yoy REAL, profit_yoy REAL,
            debt_ratio REAL, net_profit REAL, deducted_profit REAL, revenue REAL,
            ocf_to_profit REAL, ocf_abs REAL, asset_turnover REAL, ar_turnover REAL,
            fetch_success INTEGER DEFAULT 0, last_update TEXT,
            PRIMARY KEY (ts_code, report_date, report_type)
        );
        CREATE INDEX IF NOT EXISTS idx_reports_ts_type ON financial_reports(ts_code, report_type);
    """)
    conn.commit()
    return conn

def should_refresh(conn, ts_code, year) -> bool:
    cur = conn.execute("SELECT report_date, last_update FROM financial_reports WHERE ts_code=? AND report_type='annual' AND fetch_success=1 ORDER BY report_date DESC LIMIT 1", (ts_code,))
    row = cur.fetchone()
    if not row: return True
    report_year = year_of_date(str(row[0]))
    deadline = datetime(report_year + 1, Config.ANNUAL_DISCLOSURE_DEADLINE_MONTH, Config.ANNUAL_DISCLOSURE_DEADLINE_DAY)
    if datetime.now() > deadline and report_year < year: return True
    if row[1]:
        age_days = (datetime.now() - datetime.fromisoformat(row[1])).days
        if age_days > Config.CACHE_MAX_AGE_ANNUAL: return True
    return report_year < year

def save_report(conn, ts_code, report_date, metrics, success):
    now_str = datetime.now().isoformat()
    conn.execute(
        "INSERT OR REPLACE INTO financial_reports (ts_code,report_date,report_type,roe,gross_margin,net_margin,revenue_yoy,profit_yoy,debt_ratio,net_profit,deducted_profit,revenue,ocf_to_profit,ocf_abs,asset_turnover,ar_turnover,fetch_success,last_update) VALUES (?,?,'annual',?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (ts_code, report_date, metrics.get("roe"), metrics.get("gross_margin"), metrics.get("net_margin"),
         metrics.get("revenue_yoy"), metrics.get("profit_yoy"), metrics.get("debt_ratio"),
         metrics.get("net_profit"), metrics.get("deducted_profit"), metrics.get("revenue"),
         metrics.get("ocf_to_profit"), metrics.get("ocf_abs"), metrics.get("asset_turnover"),
         metrics.get("ar_turnover"), 1 if success else 0, now_str))
    conn.commit()

def save_stock_industry(conn, ts_code, name, industry_l1, industry_l2=""):
    now_str = datetime.now().isoformat()
    conn.execute("INSERT OR REPLACE INTO stocks (ts_code,name,industry_l1,industry_l2,last_industry_update,last_full_update) VALUES (?,?,?,?,?,?)",
                 (ts_code, name, industry_l1, industry_l2, now_str, now_str))
    conn.commit()

def merge_latest_reports(conn, stocks):
    """从数据库取出最新 annual 记录，与 stocks 表合并"""
    result = []
    for s in stocks:
        ts_code = s["ts_code"]
        cur = conn.execute("SELECT * FROM financial_reports WHERE ts_code=? AND report_type='annual' AND fetch_success=1 ORDER BY report_date DESC LIMIT 1", (ts_code,))
        row = cur.fetchone()
        cur2 = conn.execute("SELECT industry_l1, industry_l2 FROM stocks WHERE ts_code=?", (ts_code,))
        stock_row = cur2.fetchone()
        item = {
            "ts_code": ts_code, "name": s.get("name", ""),
            "industry_l1": stock_row[0] if stock_row else s.get("industry_l1", ""),
            "industry_l2": stock_row[1] if stock_row else "",
            "fetch_success": False,
        }
        if row:
            cols = [d[0] for d in cur.description]
            report = dict(zip(cols, row))
            item.update({
                "roe": report.get("roe"), "gross_margin": report.get("gross_margin"),
                "net_margin": report.get("net_margin"), "revenue_yoy": report.get("revenue_yoy"),
                "profit_yoy": report.get("profit_yoy"), "debt_ratio": report.get("debt_ratio"),
                "net_profit": report.get("net_profit"), "deducted_profit": report.get("deducted_profit"),
                "revenue": report.get("revenue"), "ocf_to_profit": report.get("ocf_to_profit"),
                "ocf_abs": report.get("ocf_abs"), "asset_turnover": report.get("asset_turnover"),
                "ar_turnover": report.get("ar_turnover"),
                "fetch_success": bool(report.get("fetch_success")),
                "annual_report_date": report.get("report_date"),
                "report_date": report.get("report_date"),
            })
        else:
            for f in ["roe","gross_margin","net_margin","revenue_yoy","profit_yoy","debt_ratio",
                       "net_profit","deducted_profit","revenue","ocf_to_profit","ocf_abs",
                       "asset_turnover","ar_turnover"]:
                item[f] = None
            item["annual_report_date"] = None
            item["report_date"] = None
        result.append(item)
    return result

