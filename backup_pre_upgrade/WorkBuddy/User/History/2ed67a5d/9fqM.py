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
