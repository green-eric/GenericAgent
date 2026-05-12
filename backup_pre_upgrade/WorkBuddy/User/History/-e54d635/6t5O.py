#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
A股智能选股系统 - 基于季报+年报的业绩评分系统 
架构:单季看成长,TTM看盈利与现金,最新报表看杠杆
版本: 7.0.0

数据源策略:
  成长性(营收同比and净利润同比)  -> 最新单季报
  盈利能力(ROEand毛利率and净利率) -> TTM(近4个季度滚动)
  偿债风险(资产负债率)          -> 最新单季报
  现金流质量(OCF/净利润)        -> TTM(经营现金流TTM / 净利润TTM)
  净利润(元)and经营现金流(元)      -> TTM(近4季滚动)
  年报日期                       -> 最近一期已披露年报的截止日
"""

import os
import sys
import json
import time
import logging
import argparse
import re
import sqlite3
import threading
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed, Future
from contextlib import contextmanager




class Config:
    """全局配置类"""
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    DEFAULT_STOCK_FILE = os.path.join(BASE_DIR, "xuan.txt")
    OUTPUT_DIR = BASE_DIR
    INDUSTRY_MAP_FILE = os.path.join(BASE_DIR, "industry_map.json")
    # 年报数据库路径(季报项目与年报项目共享)
    ANNUAL_DB_FILE = os.path.join(os.path.dirname(BASE_DIR), "AnnualScorer", "stock_cache.db")
    # 季报缓存数据库路径
    QUARTERLY_DB_FILE = os.path.join(BASE_DIR, "quarterly_cache.db")
    
    # --- 评分权重 ---
    WEIGHTS = {
        'growth':       0.25,   # 成长性(单季同比)
        'profitability':0.30,   # 盈利能力(TTM)
        'cash_flow':    0.20,   # 现金流质量(TTM)
        'leverage':     0.15,   # 偿债风险(最新报表)
        'valuation':    0.10    # 估值(辅助)
    }
    
    # --- 各指标满分阈值 ---
    THRESHOLDS = {
        'q_net_profit_yoy':    0.5,   # 单季净利润同比增速≥50%满分
        'q_revenue_yoy':       0.3,   # 单季营收同比增速≥30%满分
        'roe_ttm':             0.15,  # TTM ROE ≥15%满分
        'gross_margin_ttm':    0.4,   # TTM毛利率≥40%满分
        'net_profit_ratio':    1.0,   # 净现比 ≥1.0满分
        'fcf_yield':           0.03,  # 自由现金流/市值 ≥3%满分
        'de_ratio_max':        0.5,   # D/E ≤0.5满分
        'current_ratio_min':   2.0,   # 流动比率 ≥2满分
        'asset_liability_max': 0.5,   # 资产负债率 ≤50%满分
        'pe_max':             20      # PE≤20满分
    }

    FINANCE_WORKERS = 4
    API_RETRY_TIMES = 3
    API_RETRY_BACKOFF_BASE = 5.0
    API_TIMEOUT = 50
    PAUSE_CONSECUTIVE_EMPTY = 5
    PAUSE_DURATION = 30
    GLOBAL_TIMEOUT = 7200
    MIN_INDUSTRY_SAMPLES = 5
    CACHE_MAX_AGE_QUARTERLY = 30
    NEGATIVE_PROFIT_PENALTY = 15.0
    MARKET_FALLBACK_DISCOUNT = 0.95
    LOW_COMPLETENESS_PENALTY = 0.9
    ULTRA_LOW_COMPLETENESS_PENALTY = 0.75
    AKSHARE_INDUSTRY_CACHE = os.path.join(BASE_DIR, "industry_map_akshare.json")
    AKSHARE_CACHE_MAX_AGE_DAYS = 30





def setup_logging() -> logging.Logger:
    """设置日志系统(UTF-8 编码,解决乱码)"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = os.path.join(Config.BASE_DIR, f"stock_analyzer_{timestamp}.log")

    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    if hasattr(sys.stderr, 'reconfigure'):
        sys.stderr.reconfigure(encoding='utf-8')

    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)

    if not logger.handlers:
        file_handler = logging.FileHandler(log_file, encoding="utf-8", mode="w")
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

    return logger


logger = setup_logging()





@contextmanager
def db_connection(db_path: str = None):
    """数据库连接上下文管理器"""
    if db_path is None:
        db_path = ""
    conn = None
    try:
        conn = sqlite3.connect(db_path, timeout=30.0)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA busy_timeout=30000")
        yield conn
        conn.commit()
    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"数据库操作异常: {e}")
        raise
    finally:
        if conn:
            conn.close()



        conn.execute("""
            CREATE TABLE IF NOT EXISTS quarterly_reports (
                ts_code TEXT,
                report_date TEXT,
                report_type TEXT DEFAULT 'quarterly',
                -- 绝对值
                revenue REAL,              -- 营业总收入(元)
                operating_cost REAL,       -- 营业成本(元)
                net_profit REAL,           -- 归母净利润(元)
                net_profit_deducted REAL,  -- 扣非净利润(元)
                ocf_abs REAL,              -- 经营活动现金流(元)
                total_assets REAL,         -- 资产合计(元)
                total_liabilities REAL,    -- 负债合计(元)
                net_assets REAL,           -- 净资产/股东权益(元)
                -- 比率
                gross_margin REAL,         -- 销售毛利率(%)
                net_margin REAL,           -- 销售净利率(%)
                debt_ratio REAL,           -- 资产负债率(%)
                ocf_ratio REAL,            -- 净利润现金含量(%)
                roa REAL,                  -- 资产回报率ROA(%)
                -- 成长性
                revenue_yoy REAL,          -- 营业收入同比增长(%)
                profit_yoy REAL,          -- 归母净利润同比增长(%)
                -- 元数据
                fetch_success INTEGER DEFAULT 0,
                last_update TEXT,
                PRIMARY KEY (ts_code, report_date, report_type)
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS quarterly_ttm_cache (
                ts_code TEXT PRIMARY KEY,
                -- TTM绝对值
                revenue_ttm REAL,
                operating_cost_ttm REAL,
                net_profit_ttm REAL,
                ocf_abs_ttm REAL,
                net_assets_ttm REAL,       -- 最新一期净资产(用于ROE计算)
                -- TTM比率
                gross_margin_ttm REAL,
                net_margin_ttm REAL,
                ocf_ratio_ttm REAL,
                roe_ttm REAL,              -- TTM ROE(%) = 净利润TTM / 净资产
                -- 最新单季指标(用于成长性and偿债风险)
                revenue_yoy_latest REAL,
                profit_yoy_latest REAL,
                debt_ratio_latest REAL,
                total_assets_latest REAL,
                total_liabilities_latest REAL,
                -- 元数据
                quarter_count INTEGER,
                latest_quarter TEXT,
                last_update TEXT
            )
        """)
        conn.commit()
    logger.info(f"季报缓存DB初始化完成: {db_path}")




    try:
        with sqlite3.connect(db_path, timeout=10.0) as conn:
            # 检查TTM缓存
            cur = conn.execute(
                "SELECT * FROM quarterly_ttm_cache WHERE ts_code=?",
                (ts_code,)
            )
            row = cur.fetchone()
            if not row:
                return None

            # 检查缓存是否过期(默认7天)
            cols = [d[0] for d in cur.description]
            data = dict(zip(cols, row))
            last_update = data.get("last_update")
            if last_update:
                try:
                    update_time = datetime.fromisoformat(last_update)
                    age_days = (datetime.now() - update_time).total_seconds() / 86400
                    if age_days > Config.CACHE_MAX_AGE_QUARTERLY:
                        logger.debug(f"季报缓存过期 {ts_code}: {age_days:.1f}天")
                        return None
                except Exception:
                    pass
            return data
    except Exception as e:
        logger.warning(f"读取季报缓存失败 {ts_code}: {e}")
        return None



    try:
        with sqlite3.connect(db_path, timeout=10.0) as conn:
            now = datetime.now().isoformat()

            # 1. 写入各季度原始数据
            for year, q_date, block_text in blocks:
                parsed = _parse_single_block(block_text)
                report_date = f"{year}{q_date}"
                conn.execute("""
                    INSERT OR REPLACE INTO quarterly_reports
                    (ts_code, report_date, report_type,
                     revenue, operating_cost, net_profit, net_profit_deducted,
                     ocf_abs, total_assets, total_liabilities, net_assets,
                     gross_margin, net_margin, debt_ratio, ocf_ratio, roa,
                     revenue_yoy, profit_yoy, last_update)
                    VALUES (?, ?, 'quarterly',
                            ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    ts_code, report_date,
                    parsed.get("revenue"), parsed.get("operating_cost"),
                    parsed.get("net_profit"), parsed.get("net_profit_deducted"),
                    parsed.get("ocf_abs"), parsed.get("total_assets"),
                    parsed.get("total_liabilities"), parsed.get("net_assets"),
                    parsed.get("gross_margin"), parsed.get("net_margin"),
                    parsed.get("debt_ratio"), parsed.get("ocf_ratio"),
                    parsed.get("roa"),
                    parsed.get("revenue_yoy"), parsed.get("profit_yoy"),
                    now,
                ))

            # 2. 写入TTM缓存
            conn.execute("""
                INSERT OR REPLACE INTO quarterly_ttm_cache
                (ts_code,
                 revenue_ttm, operating_cost_ttm, net_profit_ttm, ocf_abs_ttm,
                 net_assets_ttm, gross_margin_ttm, net_margin_ttm,
                 ocf_ratio_ttm, roe_ttm,
                 revenue_yoy_latest, profit_yoy_latest, debt_ratio_latest,
                 total_assets_latest, total_liabilities_latest,
                 quarter_count, latest_quarter, last_update)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                ts_code,
                ttm_metrics.get("revenue_ttm"), ttm_metrics.get("cost_ttm"),
                ttm_metrics.get("net_profit_ttm"), ttm_metrics.get("ocf_abs_ttm"),
                ttm_metrics.get("net_assets_ttm"), ttm_metrics.get("gross_margin_ttm"),
                ttm_metrics.get("net_margin_ttm"), ttm_metrics.get("ocf_ratio_ttm"),
                ttm_metrics.get("roe_ttm"),
                latest_metrics.get("revenue_yoy"), latest_metrics.get("profit_yoy"),
                latest_metrics.get("debt_ratio"),
                latest_metrics.get("total_assets"), latest_metrics.get("total_liabilities"),
                len(blocks), f"{blocks[0][0]}{blocks[0][1]}" if blocks else None,
                now,
            ))
            conn.commit()
    except Exception as e:
        logger.warning(f"写入季报缓存失败 {ts_code}: {e}")





def parse_num(text: str) -> Optional[float]:
    """解析数字,支持百分比"""
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
    """从财报行提取带单位数值,单位:万亿元>亿元>万元>千元>元"""
    if not line:
        return None

    m = re.search(r"([-+]?\d+\.?\d*)\s*(万亿元|亿元|万元|千元|元)", line)
    if not m:
        return None

    val = float(m.group(1))
    unit = m.group(2)

    multipliers = {
        "万亿元": 1e12,
        "亿元": 1e8,
        "万元": 1e4,
        "千元": 1e3,
        "元": 1
    }

    return val * multipliers.get(unit, 1)


def year_of_date(date_str: str) -> int:
    """从日期字符串中提取年份"""
    if not date_str:
        return datetime.now().year
    try:
        return int(str(date_str)[:4])
    except (ValueError, IndexError):
        return datetime.now().year


# ============================================================
# 申万一级行业逻辑(与 AnnualScorer 完全一致)
# ============================================================

def load_industry_map() -> Dict[str, Any]:
    """加载本地行业映射表"""
    if os.path.exists(Config.INDUSTRY_MAP_FILE):
        try:
            with open(Config.INDUSTRY_MAP_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"加载行业映射文件失败: {e}")
    return {}


def extract_industry_from_content(text: str) -> Optional[str]:
    """从内容中提取行业信息"""
    if not text:
        return None

    patterns = [
        r"所属一级行业[::]\s*(\S+)",
        r"申万一级行业[::]\s*(\S+)",
        r"行业分类[::]\s*(\S+)"
    ]

    for pattern in patterns:
        m = re.search(pattern, text)
        if m:
            return m.group(1).strip()

    return None


def infer_industry_from_name(name: str) -> Optional[str]:
    """从股票名称推断行业"""
    if not name:
        return None

    name_keyword_industry = {
        "银行": "银行",
        "证券": "非银金融",
        "保险": "非银金融",
        "地产": "房地产",
        "房地产": "房地产",
        "钢铁": "钢铁",
        "煤炭": "煤炭",
        "有色": "有色金属",
        "化工": "基础化工",
        "医药": "医药生物",
        "生物": "医药生物",
        "电子": "电子",
        "计算机": "计算机",
        "通信": "通信",
        "汽车": "汽车",
        "机械": "机械设备",
        "电力": "公用事业",
        "食品": "食品饮料",
        "饮料": "食品饮料",
        "家电": "家用电器",
        "纺织": "纺织服饰",
        "建筑": "建筑装饰",
        "军工": "国防军工",
        "传媒": "传媒",
        "光伏": "电力设备",
        "电池": "电力设备",
        "芯片": "电子",
        "半导体": "电子"
    }

    for kw, industry in name_keyword_industry.items():
        if kw in name:
            return industry

    return None


def build_industry_map_from_akshare(
    stock_codes: Optional[List[str]] = None,
    force_refresh: bool = False
) -> Dict[str, str]:
    """
    用 akshare 获取申万一级行业分类,构建 code->industry 映射
    结果缓存到本地 JSON,默认 30 天有效
    返回: {code_short: industry_name, ...}
    """
    cache_file = Config.AKSHARE_INDUSTRY_CACHE

    if not force_refresh and os.path.exists(cache_file):
        try:
            with open(cache_file, "r", encoding="utf-8") as f:
                cached = json.load(f)
            cache_age_days = (time.time() - cached.get("_timestamp", 0)) / 86400
            if cache_age_days < Config.AKSHARE_CACHE_MAX_AGE_DAYS:
                logger.info(
                    f"使用 akshare 行业映射缓存 ({cache_age_days:.0f}天前), "
                    f"共 {len(cached)-1} 只股票"
                )
                return cached.get("data", {})
        except Exception:
            pass

    logger.info("从 akshare 获取申万一级行业分类...")
    try:
        import akshare as ak
    except ImportError:
        logger.warning("akshare 未安装,跳过申万行业获取")
        return {}

    t0 = time.time()
    result: Dict[str, str] = {}

    try:
        df_info = ak.sw_index_first_info()
        total = len(df_info)
        for i, (_, row) in enumerate(df_info.iterrows(), 1):
            ind_code = str(row["行业代码"]).split(".")[0]
            ind_name = row["行业名称"]
            try:
                df_cons = ak.index_stock_cons(symbol=ind_code)
                code_col = "品种代码"
                cnt = 0
                for _, stock in df_cons.iterrows():
                    code = str(stock[code_col])
                    if code not in result:
                        result[code] = ind_name
                        cnt += 1
                logger.info(
                    f"  [{i}/{total}] {ind_name}({ind_code}): {len(df_cons)}只, 新增{cnt}只"
                )
            except Exception as e:
                logger.warning(f"  [{i}/{total}] {ind_name}({ind_code}): 获取失败 {e}")
    except Exception as e:
        logger.error(f"akshare 申万行业获取失败: {e}")
        return result

    elapsed = time.time() - t0
    logger.info(f"akshare 行业映射完成: {len(result)}只, 耗时{elapsed:.1f}s")

    try:
        cache_data = {"_timestamp": time.time(), "data": result}
        with open(cache_file, "w", encoding="utf-8") as f:
            json.dump(cache_data, f, ensure_ascii=False)
        logger.info(f"行业映射缓存已保存: {cache_file}")
    except Exception as e:
        logger.warning(f"保存行业映射缓存失败: {e}")

    return result


def load_akshare_industry_map() -> Dict[str, str]:
    """加载 akshare 行业映射(优先缓存)"""
    cache_file = Config.AKSHARE_INDUSTRY_CACHE
    if os.path.exists(cache_file):
        try:
            with open(cache_file, "r", encoding="utf-8") as f:
                cached = json.load(f)
            return cached.get("data", {})
        except Exception:
            pass
    return {}





def determine_industry(
    ts_code: str,
    name: str,
    content: str,
    industry_map: Dict[str, Any],
    use_api: bool = True,
    session: Optional[req_lib.Session] = None,
    akshare_map: Optional[Dict[str, str]] = None
) -> Optional[str]:
    """
    确定股票所属行业(混合策略,优先级从高到低)- 与 AnnualScorer 一致

    优先级:
      1. 原文提取      — 最准确,公司自己披露
      2. akshare 申万   — 权威分类,100%覆盖,本地缓存
      3. 股票名称推断   — 关键词匹配,快速无网络
      4. NeoData API    — 大模型查询,补漏用
      5. 本地静态映射表  — 历史遗留数据,质量参差
      6. 代码前缀兜底   — 最弱保底
    """
    code_short = ts_code.split(".")[0]

    # 1. 从原文中提取
    ind = extract_industry_from_content(content)
    if ind:
        return ind

    # 2. akshare 申万一级行业分类
    if akshare_map is None:
        akshare_map = load_akshare_industry_map()
    ind = akshare_map.get(code_short)
    if ind:
        return ind

    # 3. 从股票名称关键词推断
    ind = infer_industry_from_name(name)
    if ind:
        return ind

    

    # 5. 本地静态映射表
    def _get_industry_l1(key: str) -> Optional[str]:
        val = industry_map.get(key)
        if val is None:
            return None
        if isinstance(val, str):
            return val
        if isinstance(val, dict):
            return val.get("industry_l1")
        return None

    ind = _get_industry_l1(ts_code)
    if ind:
        return ind
    ind = _get_industry_l1(code_short)
    if ind:
        return ind

    # 6. 代码前缀兜底
    code_prefix_industry = {
        "60": "机械设备",
        "00": "房地产",
        "30": "医药生物",
        "68": "电子"
    }
    return code_prefix_industry.get(code_short[:2])





# ============================================================
# 季报数据获取(多季度TTM + 单季指标)
# ============================================================


    Args:
        - report_date: "YYYYMMDD" 字符串
        - report_type: "Q1单季报"/"Q2单季报"/"Q3单季报"/"Q4单季报"/"年报"
        - section_text: 该段落的正文内容
    """
    if not text:
        return []

    # 匹配每个独立财报子段落的起始标记
    # 格式: 根据...在A股市场YYYYMMDD发布的财报数据,统计截止日期为YYYYMMDD的Qx单季报/年报
    pattern = (
        r"根据.+?在A股市场\d+发布的财报数据[,,]\s*"
        r"统计截止日期为(\d{4})(0331|0630|0930|1231)的"
        r"(Q[1-4]单?季报|年报)"
    )
    matches = list(re.finditer(pattern, text))

    if not matches:
        return []

    sections = []
    for i, m in enumerate(matches):
        year = m.group(1)
        q_date = m.group(2)
        report_type = m.group(3)
        report_date = f"{year}{q_date}"

        # 从当前匹配的结束位置开始,到下一个匹配的开始位置
        start = m.end()
        if i + 1 < len(matches):
            end = matches[i + 1].start()
        else:
            end = len(text)
        section_text = text[start:end].strip()
        sections.append((report_date, report_type, section_text))

    # 按时间降序排列(最新的在前)
    sections.sort(key=lambda x: x[0], reverse=True)
    return sections


def _extract_all_quarterly_blocks(text: str) -> List[Tuple[str, str, str]]:
    """
    从NeoData返回中提取所有季报段落(兼容旧接口)
    返回: [(year, quarter_date, block_text), ...] 按时间降序排列

    此函数已废弃,建议使用 _extract_all_report_sections 代替.
    保留此函数仅为兼容 _compute_ttm 等旧代码的调用.
    """
    sections = _extract_all_report_sections(text)
    # 转换为旧格式: (year, quarter_date, block_text)
    # 注意:旧格式不含 report_type,调用方需注意
    return [(date[:4], date[4:], text) for date, _, text in sections]


def _parse_single_block(block: str) -> Dict[str, Optional[float]]:
    """从单个季报段落提取所有可用指标(含ROE计算所需字段)"""
    result = {
        "revenue": None,              # 营业总收入(元)
        "operating_cost": None,       # 营业成本(元)
        "net_profit": None,           # 归母净利润(元)
        "net_profit_deducted": None,  # 扣非净利润(元)
        "gross_margin": None,         # 销售毛利率(%)
        "net_margin": None,           # 销售净利率(%)
        "revenue_yoy": None,          # 营业收入同比增长(%)
        "profit_yoy": None,           # 归母净利润同比增长(%)
        "ocf_ratio": None,            # 净利润现金含量(%)
        "ocf_abs": None,              # 经营活动现金流(元)
        "total_assets": None,         # 资产合计(元)
        "total_liabilities": None,    # 负债合计(元)
        "net_assets": None,           # 净资产/股东权益(元)
        "debt_ratio": None,           # 资产负债率(%)
        "roa": None,                  # 资产回报率ROA(%)
    }

    if not block:
        return result

    for line in block.split("\n"):
        line = line.strip()
        if not line:
            continue

        # 营业总收入 — 只取第一个值(防止多季度混合block中被覆盖)
        if "营业总收入" in line and "同比" not in line and "环比" not in line:
            if result["revenue"] is None:
                val = _parse_num_from_line(line)
                if val is not None:
                    result["revenue"] = val

        # 营业成本 — 只取第一个值
        elif "营业成本" in line and "同比" not in line and "环比" not in line and "营业总成本" not in line:
            if result["operating_cost"] is None:
                val = _parse_num_from_line(line)
                if val is not None:
                    result["operating_cost"] = val

        # 归母净利润 — 严格行首匹配^归母净利润,排除同比/扣非/现金含量
        elif re.match(r"^归母净利润", line) and "同比" not in line and "环比" not in line and "扣非" not in line and "现金" not in line:
            if result["net_profit"] is None:
                val = _parse_num_from_line(line)
                if val is not None:
                    result["net_profit"] = val

        # 扣非净利润 — 只取第一个值
        elif "扣非净利润" in line and "同比" not in line and "环比" not in line:
            if result["net_profit_deducted"] is None:
                val = _parse_num_from_line(line)
                if val is not None:
                    result["net_profit_deducted"] = val

        # 销售毛利率 — 只取第一个值
        elif "销售毛利率" in line or ("毛利率" in line and "同比" not in line and "环比" not in line):
            if result["gross_margin"] is None:
                m = re.search(r"毛利率[::\s]*([-+]?\d+\.?\d*)%", line)
                if m:
                    result["gross_margin"] = float(m.group(1))

        # 销售净利率 — 只取第一个值
        elif "销售净利率" in line or ("净利率" in line and "同比" not in line and "环比" not in line):
            if result["net_margin"] is None:
                m = re.search(r"净利率[::\s]*([-+]?\d+\.?\d*)%", line)
                if m:
                    result["net_margin"] = float(m.group(1))

        # 营业收入同比增长 — 只取第一个值
        elif any(kw in line for kw in ["营业收入同比增长", "营收同比增长", "营业总收入同比增长"]):
            if result["revenue_yoy"] is None:
                result["revenue_yoy"] = parse_num(line)

        # 归母净利润同比增长 — 只取第一个值
        elif "归母净利润同比增长" in line or ("净利润同比增长" in line and "归母" in line):
            if result["profit_yoy"] is None:
                result["profit_yoy"] = parse_num(line)

        # 净利润现金含量(OCF/净利润) — 只取第一个值
        elif "净利润现金含量" in line:
            if result["ocf_ratio"] is None:
                m = re.search(r"净利润现金含量[::\s]*([-+]?\d+\.?\d*)%", line)
                if m:
                    result["ocf_ratio"] = float(m.group(1))

        # 经营活动产生的现金流量净额 — 只取第一个值(排除"每股"版本)
        elif "经营活动产生的现金流量净额" in line and "每股" not in line:
            if result["ocf_abs"] is None:
                val = _parse_num_from_line(line)
                if val is not None:
                    result["ocf_abs"] = val

        # 资产合计 — 只取第一个值
        elif "资产合计" in line and "同比" not in line:
            if result["total_assets"] is None:
                val = _parse_num_from_line(line)
                if val is not None:
                    result["total_assets"] = val

        # 负债合计 — 只取第一个值
        elif "负债合计" in line and "同比" not in line:
            if result["total_liabilities"] is None:
                val = _parse_num_from_line(line)
                if val is not None:
                    result["total_liabilities"] = val

        # 资产负债率 — 直接提取(不通过负债/资产计算)
        elif "资产负债率" in line and "同比" not in line:
            if result.get("debt_ratio") is None:
                m = re.search(r"资产负债率[::\s]*([-+]?\d+\.?\d*)%", line)
                if m:
                    result["debt_ratio"] = float(m.group(1))

        # 净资产/股东权益(多种表述)— 只取第一个值
        elif any(kw in line for kw in ["股东权益合计", "所有者权益合计", "归母净资产", "归母股东权益"]):
            if result["net_assets"] is None:
                val = _parse_num_from_line(line)
                if val is not None:
                    result["net_assets"] = val

        # 资产回报率ROA — 只取第一个值
        elif "资产回报率" in line or "ROA" in line.upper():
            if result["roa"] is None:
                m = re.search(r"(?:资产回报率|ROA)[::\s]*([-+]?\d+\.?\d*)%", line)
                if m:
                    result["roa"] = float(m.group(1))

    # 如果没有直接的净资产数据,用 资产合计 - 负债合计 计算
    if result["net_assets"] is None and result["total_assets"] is not None and result["total_liabilities"] is not None:
        result["net_assets"] = result["total_assets"] - result["total_liabilities"]

    # 如果没有直接的资产负债率,用 负债合计 / 资产合计 计算
    if result["debt_ratio"] is None and result["total_assets"] is not None and result["total_liabilities"] is not None and result["total_assets"] > 0:
        result["debt_ratio"] = round(result["total_liabilities"] / result["total_assets"] * 100, 2)

    return result


def _compute_ttm(blocks: List[Tuple[str, str, str]]) -> Dict[str, Optional[float]]:
    """
    从多个季报段落计算TTM(近4个季度滚动)值
    
    TTM计算逻辑:
    - 营业总收入TTM = 最近4个季度营业总收入之和
    - 归母净利润TTM = 最近4个季度归母净利润之和
    - 毛利率TTM = (营收TTM - 成本TTM) / 营收TTM * 100
    - 净利率TTM = 净利润TTM / 营收TTM * 100
    - OCF_TTM = 净利润现金含量加权平均 * 净利润TTM
    - OCF/净利润_TTM = OCF_TTM / 净利润TTM * 100
    
    注意:如果不足4个季度,用已有季度计算
    """
    ttm = {
        "revenue_ttm": None,
        "operating_cost_ttm": None,
        "net_profit_ttm": None,
        "gross_margin_ttm": None,
        "net_margin_ttm": None,
        "ocf_abs_ttm": None,       # TTM经营现金流绝对值
        "ocf_ratio_ttm": None,     # TTM OCF/净利润(%)
        "roe_ttm": None,           # TTM ROE (暂不支持,需要净资产数据)
    }

    if not blocks:
        return ttm

    # 取最多4个季度
    recent_blocks = blocks[:4]

    revenue_sum = 0.0
    cost_sum = 0.0
    profit_sum = 0.0
    ocf_abs_sum = 0.0
    has_revenue = False
    has_cost = False
    has_profit = False
    has_ocf = False

    for year, q_date, block_text in recent_blocks:
        metrics = _parse_single_block(block_text)

        rev = metrics.get("revenue")
        if rev is not None:
            revenue_sum += rev
            has_revenue = True

        cost = metrics.get("operating_cost")
        if cost is not None:
            cost_sum += cost
            has_cost = True

        profit = metrics.get("net_profit")
        if profit is not None:
            profit_sum += profit
            has_profit = True

        # OCF:优先直接使用经营活动产生的现金流量净额
        ocf_abs_val = metrics.get("ocf_abs")
        if ocf_abs_val is not None:
            ocf_abs_sum += ocf_abs_val
            has_ocf = True
        else:
            # 兜底:用净利润现金含量 * 净利润计算
            ocf_ratio = metrics.get("ocf_ratio")
            if ocf_ratio is not None and profit is not None:
                ocf_abs_sum += profit * (ocf_ratio / 100.0)
                has_ocf = True

    if has_revenue:
        ttm["revenue_ttm"] = revenue_sum
    if has_cost:
        ttm["operating_cost_ttm"] = cost_sum
    if has_profit:
        ttm["net_profit_ttm"] = profit_sum
    if has_ocf:
        ttm["ocf_abs_ttm"] = ocf_abs_sum

    # 毛利率TTM = (营收TTM - 成本TTM) / 营收TTM * 100
    if has_revenue and has_cost and revenue_sum > 0:
        ttm["gross_margin_ttm"] = round((revenue_sum - cost_sum) / revenue_sum * 100, 2)

    # 净利率TTM = 净利润TTM / 营收TTM * 100
    if has_revenue and has_profit and revenue_sum > 0:
        ttm["net_margin_ttm"] = round(profit_sum / revenue_sum * 100, 2)

    # OCF/净利润TTM
    if has_profit and has_ocf and profit_sum != 0:
        ttm["ocf_ratio_ttm"] = round(ocf_abs_sum / profit_sum * 100, 2)

    # TTM ROE = 净利润TTM / 最新一期净资产 * 100
    # 净资产取最新一期的值(时点数,不用TTM累加)
    # 注意:很多单季报(Q2/Q3/Q4)不含资产负债表,需要往前遍历所有段落找净资产
    if has_profit and profit_sum != 0:
        net_assets = None
        # 先尝试从最新单季报取
        latest_block = recent_blocks[0]
        latest_metrics = _parse_single_block(latest_block[2])
        net_assets = latest_metrics.get("net_assets")
        
        # 如果最新单季报没有净资产,往前遍历所有段落(包括不足4个季度的)
        if net_assets is None or net_assets <= 0:
            for year, q_date, block_text in blocks:
                m = _parse_single_block(block_text)
                na = m.get("net_assets")
                if na is not None and na > 0:
                    net_assets = na
                    break
        
        if net_assets and net_assets > 0:
            ttm["roe_ttm"] = round(profit_sum / net_assets * 100, 2)
            ttm["net_assets_ttm"] = net_assets  # 保存净资产用于展示

    return ttm
    """
    指标计算器 - 基于DataFrame计算各种财务指标
    
    功能:
    - 单季拆分:将累计值拆分为单季值
    - TTM计算:最近4个季度滚动计算
    - 杠杆计算:最新报表的存量指标
    """
    
    def __init__(self, df: pd.DataFrame):
        """
        初始化指标计算器
        
        Args:
            df: akshare财务数据DataFrame
                Columns: report_date, revenue, operating_cost, 
                        net_profit, total_assets, total_liabilities,
                        equity_parent, ocf_abs, gross_margin, net_margin,
                        revenue_yoy, profit_yoy, debt_ratio
        """
        self.df = df.sort_values("report_date", ascending=False).copy()
        self._split_quarterly()
        self._calc_ttm_and_leverage()
    
    def _split_quarterly(self):
        """单季拆分:将累计值拆分为单季值"""
        # 按报告期月份判断季度
        self.df['month'] = self.df['report_date'].astype(str).str[4:6].astype(int)
        self.df['year'] = self.df['report_date'].astype(str).str[:4].astype(int)
        
        for col in ['revenue', 'operating_cost', 'net_profit']:
            q_col = f'q_{col}'
            self.df[q_col] = None
            
            for idx, row in self.df.iterrows():
                month = row['month']
                
                if month == 3:  # Q1
                    self.df.at[idx, q_col] = row[col]
                elif month == 6:  # Q2
                    prev_row = self.df[(self.df['year'] == row['year']) & (self.df['month'] == 3)]
                    if not prev_row.empty:
                        self.df.at[idx, q_col] = row[col] - prev_row.iloc[0][col]
                    else:
                        self.df.at[idx, q_col] = row[col]
                elif month == 9:  # Q3
                    prev_row = self.df[(self.df['year'] == row['year']) & (self.df['month'] == 6)]
                    if not prev_row.empty:
                        self.df.at[idx, q_col] = row[col] - prev_row.iloc[0][col]
                    else:
                        self.df.at[idx, q_col] = row[col]
                elif month == 12:  # Q4
                    prev_row = self.df[(self.df['year'] == row['year']) & (self.df['month'] == 9)]
                    if not prev_row.empty:
                        self.df.at[idx, q_col] = row[col] - prev_row.iloc[0][col]
                    else:
                        self.df.at[idx, q_col] = row[col]
        
        # 清理临时列
        self.df.drop(['month', 'year'], axis=1, inplace=True)
    
    def _find_last_year_quarter(self, current_date: str) -> Optional[str]:
        """找到去年同期的报告期"""
        year = int(current_date[:4])
        month = int(current_date[4:6])
        
        # 确定当前季度的月份
        if month in [3]:  # Q1
            last_year_month = 3
        elif month in [6]:  # Q2
            last_year_month = 6
        elif month in [9]:  # Q3
            last_year_month = 9
        elif month in [12]:  # Q4
            last_year_month = 12
        else:
            return None
            
        last_year_date = f"{year-1}{last_year_month:02d}31" if last_year_month != 12 else f"{year-1}1231"
        
        # 在DataFrame中查找
        match = self.df[self.df['report_date'] == last_year_date]
        return last_year_date if not match.empty else None
    
    def _calc_ttm_and_leverage(self):
        """计算TTM指标和杠杆指标"""
        # TTM计算(最近4个季度)
        recent_quarters = self.df.head(4)
        
        # 营收TTM
        revenue_sum = recent_quarters['revenue'].sum() if 'revenue' in recent_quarters.columns else None
        self.ttm_revenue = round(revenue_sum, 2) if revenue_sum is not None else None
        
        # 成本TTM
        cost_sum = recent_quarters['operating_cost'].sum() if 'operating_cost' in recent_quarters.columns else None
        self.ttm_oper_cost = round(cost_sum, 2) if cost_sum is not None else None
        
        # 净利润TTM
        profit_sum = recent_quarters['net_profit'].sum() if 'net_profit' in recent_quarters.columns else None
        self.ttm_net_profit = round(profit_sum, 2) if profit_sum is not None else None
        
        # 经营现金流TTM - 直接使用ocf_abs字段
        ocf_sum = recent_quarters['ocf_abs'].sum() if 'ocf_abs' in recent_quarters.columns else None
        self.ttm_ocf = round(ocf_sum, 2) if ocf_sum is not None else None
        
        # 毛利率TTM
        if self.ttm_revenue and self.ttm_oper_cost and self.ttm_revenue > 0:
            self.gross_margin_ttm = round((self.ttm_revenue - self.ttm_oper_cost) / self.ttm_revenue * 100, 2)
        else:
            self.gross_margin_ttm = None
            
        # 净利率TTM
        if self.ttm_revenue and self.ttm_net_profit and self.ttm_revenue > 0:
            self.net_margin_ttm = round(self.ttm_net_profit / self.ttm_revenue * 100, 2)
        else:
            self.net_margin_ttm = None
            
        # TTM ROE(需要净资产数据)
        if self.ttm_net_profit and self.latest_net_assets and self.ttm_net_profit != 0:
            self.roe_ttm = round(self.ttm_net_profit / self.latest_net_assets * 100, 2)
        else:
            self.roe_ttm = None
        
        # 最新单季指标
        latest = self.df.iloc[0] if not self.df.empty else None
        
        # 营收同比(最新单季往前找)
        # 首先尝试从最新单季报取
        if latest and 'revenue_yoy' in latest and latest['revenue_yoy'] is not None:
            self.q_revenue_yoy = latest['revenue_yoy']
        else:
            # 往前遍历所有报告期找营收同比,优先找单季报
            found = False
            for idx in range(len(self.df)):
                row = self.df.iloc[idx]
                if 'revenue_yoy' in row and row['revenue_yoy'] is not None:
                    self.q_revenue_yoy = row['revenue_yoy']
                    found = True
                    break
            if not found:
                self.q_revenue_yoy = None
        
        # 净利润同比(最新单季)
        if latest and 'profit_yoy' in latest and latest['profit_yoy'] is not None:
            self.q_net_profit_yoy = latest['profit_yoy']
        else:
            # 往前遍历所有报告期找净利润同比
            found = False
            for idx in range(len(self.df)):
                row = self.df.iloc[idx]
                if 'profit_yoy' in row and row['profit_yoy'] is not None:
                    self.q_net_profit_yoy = row['profit_yoy']
                    found = True
                    break
            if not found:
                self.q_net_profit_yoy = None
        
        # 营业利润同比(最新单季)
        if latest and 'q_oper_profit_yoy' in latest and latest['q_oper_profit_yoy'] is not None:
            self.q_oper_profit_yoy = latest['q_oper_profit_yoy']
        else:
            self.q_oper_profit_yoy = None
        
        # 资产负债率(最新单季)
        if latest and 'debt_ratio' in latest and latest['debt_ratio'] is not None:
            self.asset_liability_ratio = latest['debt_ratio']
        else:
            # 兜底:用负债/资产计算
            if latest and 'total_liabilities' in latest and 'total_assets' in latest:
                if latest['total_assets'] and latest['total_assets'] > 0:
                    self.asset_liability_ratio = round(latest['total_liabilities'] / latest['total_assets'] * 100, 2)
                else:
                    self.asset_liability_ratio = None
            else:
                self.asset_liability_ratio = None
        
        # 最新财务数据(用于展示)
        if latest:
            self.latest_total_assets = latest.get('total_assets')
            self.latest_total_liab = latest.get('total_liabilities')
            self.latest_equity_parent = latest.get('equity_parent')
            self.latest_net_assets = latest.get('equity_parent')  # 使用股东权益作为净资产
        else:
            self.latest_total_assets = None
            self.latest_total_liab = None
            self.latest_equity_parent = None
            self.latest_net_assets = None
        
        # 其他指标
        self.de_ratio = None  # D/E比率
        self.current_ratio = None  # 流动比率
        self.interest_cover = None  # 利息覆盖倍数
        self.fcf_ttm = None  # 自由现金流TTM
        self.net_profit_ratio = None  # 净现比
        self.cash_recovery_rate = None  # 销售收现比
        self.ocf_ttm = None  # OCF TTM(已计算)



def get_combined_financials(symbol):
    """获取股票三大报表数据并合并"""
    try:
        import pandas as pd
        import akshare as ak

        # 获取利润表
        income_df = ak.stock_financial_analysis_indicator(symbol, "income")
        if not income_df.empty:
            income_df = income_df[['report_date', '营业收入', '营业成本', '营业利润', '净利润',
                                 '营业收入同比增长', '净利润同比增长']].copy()
            income_df.columns = ['report_date', 'revenue', 'operating_cost', 'oper_profit', 'net_profit',
                               'revenue_yoy', 'profit_yoy']

            # 获取资产负债表
            balance_df = ak.stock_financial_analysis_indicator(symbol, "balancesheet")
            if not balance_df.empty:
                balance_df = balance_df[['report_date', '资产总计', '负债合计', '股东权益合计']].copy()
                balance_df.columns = ['report_date', 'total_assets', 'total_liabilities', 'equity_parent']

            # 获取现金流量表
            cashflow_df = ak.stock_financial_analysis_indicator(symbol, "cashflow")
            if not cashflow_df.empty:
                cashflow_df = cashflow_df[['report_date', '经营活动产生的现金流量净额']].copy()
                cashflow_df.columns = ['report_date', 'ocf_abs']

            # 合并数据
            merged = income_df.copy()
            if not balance_df.empty:
                merged = merged.merge(balance_df, on='report_date', how='left')
            if not cashflow_df.empty:
                merged = merged.merge(cashflow_df, on='report_date', how='left')

            return merged.sort_values('report_date', ascending=False).reset_index(drop=True)

        return pd.DataFrame()
    except Exception as e:
        print(f"获取{symbol}财务数据失败: {e}")
        return pd.DataFrame()

def fetch_quarterly_data(
    ts_code: str,
    name: str,
    token: str
) -> Dict[str, Any]:
    """
    获取单只股票季报数据,返回:
    - TTM指标(盈利and现金流)
    - 最新单季指标(成长性and偿债风险)

    V7.0: 优先读取缓存DB,无有效缓存时调用API
    """
    # 1. 先检查缓存
    cached = _load_quarterly_from_db(ts_code)
    if cached:
        logger.debug(f"使用季报缓存 {ts_code}")
        return {
            "ttm_metrics": {
                "roe_ttm": cached.get("roe_ttm"),
                "gross_margin_ttm": cached.get("gross_margin_ttm"),
                "net_margin_ttm": cached.get("net_margin_ttm"),
                "ocf_ratio_ttm": cached.get("ocf_ratio_ttm"),
                "revenue_ttm": cached.get("revenue_ttm"),
                "cost_ttm": cached.get("operating_cost_ttm"),
                "net_profit_ttm": cached.get("net_profit_ttm"),
                "ocf_abs_ttm": cached.get("ocf_abs_ttm"),
                "net_assets_ttm": cached.get("net_assets_ttm"),
            },
            "latest_quarterly": {
                "revenue_yoy": cached.get("revenue_yoy_latest"),
                "profit_yoy": cached.get("profit_yoy_latest"),
                "debt_ratio": cached.get("debt_ratio_latest"),
                "total_assets": cached.get("total_assets_latest"),
                "total_liabilities": cached.get("total_liabilities_latest"),
            },
            "content": "",
            "fetch_success": True,
            "quarter_count": cached.get("quarter_count", 0),
            "latest_quarter": cached.get("latest_quarter", ""),
        }

    # 2. 调用AkShare获取财务数据
    try:
        df_fin = get_combined_financials(ts_code)
        if df_fin.empty:
            logger.warning(f"获取 {ts_code} 财务数据失败: 返回空DataFrame")
            return {
                "ttm_metrics": {},
                "latest_quarterly": {},
                "content": "",
                "fetch_success": False,
                "quarter_count": 0,
                "latest_quarter": "",
            }
