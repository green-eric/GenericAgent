#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
全字段验证脚本 V1.0
对随机选取的股票，验证 stock_analyzer.py 所有输出字段的正确性。
"""
import os, sys, json, logging, time, re
from datetime import datetime

# 确保能 import stock_analyzer
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

import requests as req_lib
from requests.adapters import HTTPAdapter

# ============================================================
# 配置
# ============================================================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)

NEODATA_URL = "https://copilot.tencent.com/agenttool/v1/neodata"
TOKEN_FILE = os.path.expanduser("~/.workbuddy/.neodata_token")
API_TIMEOUT = 50
API_RETRY_TIMES = 2

def load_token():
    with open(TOKEN_FILE, "r", encoding="utf-8") as f:
        return f.read().strip()

def run_neodata(query, token, timeout=API_TIMEOUT):
    """调用 NeoData API，正确解析 apiRecall 结构"""
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    payload = {"query": query}
    for attempt in range(1, API_RETRY_TIMES + 2):
        try:
            resp = req_lib.post(NEODATA_URL, json=payload, headers=headers, timeout=timeout)
            resp.raise_for_status()
            data = resp.json()
            inner = data.get("data", {})
            if isinstance(inner, dict):
                api_data = inner.get("apiData", {})
                recall_list = api_data.get("apiRecall", [])
                if isinstance(recall_list, list) and recall_list:
                    for item in recall_list:
                        content = item.get("content", "")
                        if content and "统计截止日期为" in content and "年报" in content:
                            return content
                    for item in recall_list:
                        content = item.get("content", "")
                        if content and "财务" in item.get("type", ""):
                            return content
                    parts = [item.get("content", "") for item in recall_list if item.get("content")]
                    if parts:
                        return "\n\n".join(parts)
                if isinstance(inner.get("text"), str) and inner["text"]:
                    return inner["text"]
            elif isinstance(inner, str):
                return inner
            return json.dumps(data, ensure_ascii=False)
        except Exception as e:
            logger.warning(f"API error (attempt {attempt}): {e}")
            if attempt < API_RETRY_TIMES + 1:
                time.sleep(3 ** attempt)
    return ""

# ============================================================
# 导入 stock_analyzer 的解析函数
# ============================================================
from stock_analyzer import (
    _extract_annual_block, parse_financial_all, parse_num,
    _parse_num_from_line, calc_completeness, calc_score,
    CORE_METRICS, MOCK_NEODATA_RESPONSE
)

# ============================================================
# 字段定义
# ============================================================
FINANCE_FIELDS = [
    "roe", "gross_margin", "net_margin",
    "revenue_yoy", "profit_yoy",
    "debt_ratio",
    "net_profit", "deducted_profit", "revenue",
    "ocf_to_profit", "ocf_abs",
    "asset_turnover", "ar_turnover",
]

SCORE_FIELDS = [
    "total_score", "profit_score", "growth_score",
    "ocf_score", "debt_score",
]

META_FIELDS = [
    "ts_code", "name", "industry_l1",
    "grade", "confidence",
    "completeness", "completeness_level",
    "fetch_success", "annual_report_date",
    "market_fallback",
]

ALL_FIELDS = FINANCE_FIELDS + SCORE_FIELDS + META_FIELDS

# ============================================================
# 测试股票（覆盖不同行业、不同市值）
# ============================================================
TEST_STOCKS = [
    {"ts_code": "000001.SZ", "name": "平安银行"},    # 银行
    {"ts_code": "000002.SZ", "name": "万科A"},       # 房地产
    {"ts_code": "600519.SH", "name": "贵州茅台"},    # 食品饮料
    {"ts_code": "300750.SZ", "name": "宁德时代"},    # 电力设备
    {"ts_code": "002594.SZ", "name": "比亚迪"},      # 汽车
    {"ts_code": "601318.SH", "name": "中国平安"},    # 非银金融
    {"ts_code": "000858.SZ", "name": "五粮液"},      # 食品饮料
    {"ts_code": "600036.SH", "name": "招商银行"},    # 银行
    {"ts_code": "002415.SZ", "name": "海康威视"},    # 计算机
    {"ts_code": "601012.SH", "name": "隆基绿能"},    # 电力设备
]

# ============================================================
# 验证逻辑
# ============================================================
def fetch_and_parse(ts_code, name, token):
    """获取单只股票数据并解析"""
    query = f"{ts_code} {name} 年报"
    text = run_neodata(query, token)
    if not text:
        return None, "API_EMPTY"
    block = _extract_annual_block(text)
    if not block:
        return None, "NO_ANNUAL_BLOCK"
    metrics = parse_financial_all(block)
    m = re.search(r"统计截止日期为(\d{4})1231的年报", text)
    report_date = m.group(1) + "1231" if m else ""
    metrics["fetch_success"] = True
    metrics["annual_report_date"] = report_date
    metrics["report_date"] = report_date
    return metrics, "OK"

def validate_finance_fields(metrics):
    """验证财务字段：检查类型、单位、合理性"""
    issues = []
    checks = {}

    for field in FINANCE_FIELDS:
        val = metrics.get(field)
        checks[field] = val

        # 类型检查
        if val is not None and not isinstance(val, (int, float)):
            issues.append(f"[TYPE] {field}: 期望数值, 实际 {type(val).__name__}={val}")

    # 合理性检查
    roe = metrics.get("roe")
    if roe is not None and abs(roe) > 200:
        issues.append(f"[RANGE] roe={roe}% 超出合理范围(-200%~200%)")

    gm = metrics.get("gross_margin")
    if gm is not None and (gm < -100 or gm > 100):
        issues.append(f"[RANGE] gross_margin={gm}% 超出合理范围")

    nm = metrics.get("net_margin")
    if nm is not None and (nm < -200 or nm > 100):
        issues.append(f"[RANGE] net_margin={nm}% 超出合理范围")

    dr = metrics.get("debt_ratio")
    if dr is not None and (dr < 0 or dr > 100):
        issues.append(f"[RANGE] debt_ratio={dr}% 应在0~100之间")

    np_val = metrics.get("net_profit")
    if np_val is not None and abs(np_val) > 1e14:
        issues.append(f"[RANGE] net_profit={np_val} 超出合理范围(>100万亿)")

    rev = metrics.get("revenue")
    if rev is not None and rev < 0:
        issues.append(f"[RANGE] revenue={rev} 不应为负数")

    ocf = metrics.get("ocf_abs")
    ocf_ratio = metrics.get("ocf_to_profit")
    if ocf_ratio is not None and abs(ocf_ratio) > 5000:
        issues.append(f"[RANGE] ocf_to_profit={ocf_ratio}% 超出合理范围")

    at = metrics.get("asset_turnover")
    if at is not None and at < 0:
        issues.append(f"[RANGE] asset_turnover={at} 不应为负数")

    art = metrics.get("ar_turnover")
    if art is not None and art < 0:
        issues.append(f"[RANGE] ar_turnover={art} 不应为负数")

    # 净利润单位检查（应为元级，即至少百万以上）
    if np_val is not None and abs(np_val) < 1000 and np_val != 0:
        issues.append(f"[UNIT] net_profit={np_val} 疑似单位错误（太小，可能漏了万元/亿元转换）")

    # revenue 单位检查
    if rev is not None and rev < 10000 and rev > 0:
        issues.append(f"[UNIT] revenue={rev} 疑似单位错误（太小）")

    return checks, issues

def validate_score_fields(score_result):
    """验证评分字段"""
    issues = []
    checks = {}

    for field in SCORE_FIELDS:
        val = score_result.get(field)
        checks[field] = val
        if val is not None and not isinstance(val, (int, float)):
            issues.append(f"[TYPE] {field}: 期望数值, 实际 {type(val).__name__}={val}")

    total = score_result.get("total_score")
    if total is not None:
        if total < 0 or total > 100:
            issues.append(f"[RANGE] total_score={total} 超出0~100范围")

    # 子项分应在合理范围
    for f in ["profit_score", "growth_score", "ocf_score", "debt_score"]:
        v = score_result.get(f)
        if v is not None and (v < 0 or v > 110):
            issues.append(f"[RANGE] {f}={v} 超出合理范围")

    return checks, issues

def validate_meta_fields(score_result):
    """验证元数据字段"""
    issues = []
    checks = {}

    for field in META_FIELDS:
        val = score_result.get(field)
        checks[field] = val

    # ts_code 格式
    ts_code = score_result.get("ts_code")
    if ts_code and not re.match(r"^\d{6}\.(SH|SZ)$", str(ts_code)):
        issues.append(f"[FORMAT] ts_code={ts_code} 格式不正确")

    # grade 枚举
    grade = score_result.get("grade")
    if grade and grade not in ("A", "B", "C", "D", "E"):
        issues.append(f"[ENUM] grade={grade} 不在ABCDE中")

    # confidence 枚举
    conf = score_result.get("confidence")
    if conf and conf not in ("高", "中", "低"):
        issues.append(f"[ENUM] confidence={conf} 不在高/中/低中")

    # completeness 范围
    comp = score_result.get("completeness")
    if comp is not None and (comp < 0 or comp > 1):
        issues.append(f"[RANGE] completeness={comp} 应在0~1之间")

    # completeness_level 枚举
    comp_level = score_result.get("completeness_level")
    if comp_level and comp_level not in ("high", "medium", "low", "ultra_low"):
        issues.append(f"[ENUM] completeness_level={comp_level} 不在high/medium/low/ultra_low中")

    # fetch_success 类型
    fs = score_result.get("fetch_success")
    if fs is not None and not isinstance(fs, bool):
        issues.append(f"[TYPE] fetch_success={fs} 应为bool")

    # market_fallback 类型
    mf = score_result.get("market_fallback")
    if mf is not None and not isinstance(mf, bool):
        issues.append(f"[TYPE] market_fallback={mf} 应为bool")

    # annual_report_date 格式
    ard = score_result.get("annual_report_date")
    if ard and not re.match(r"^\d{8}$", str(ard)):
        issues.append(f"[FORMAT] annual_report_date={ard} 格式应为YYYYMMDD")

    return checks, issues

# ============================================================
# 自测数据验证
# ============================================================
def test_mock_data():
    """用 mock 数据验证所有财务字段解析"""
    logger.info("=" * 70)
    logger.info("第1阶段: Mock 数据验证（所有13个财务字段）")
    logger.info("=" * 70)

    block = _extract_annual_block(MOCK_NEODATA_RESPONSE)
    metrics = parse_financial_all(block)

    expected = {
        "roe": 15.67,
        "gross_margin": 42.35,
        "net_margin": 18.22,
        "revenue_yoy": 28.45,
        "profit_yoy": 35.67,
        "debt_ratio": 38.92,
        "net_profit": 1642130865.33,
        "deducted_profit": 1523456789.01,
        "revenue": 18654321098.76,
        "ocf_abs": 2156789012.34,
        "ocf_to_profit": round(2156789012.34 / 1642130865.33 * 100, 2),
        "asset_turnover": 0.85,
        "ar_turnover": 6.78,
    }

    passed = 0
    failed = 0
    for field, exp_val in expected.items():
        actual = metrics.get(field)
        if actual is None:
            logger.error(f"  [FAIL] {field}: 期望 {exp_val}, 实际 None")
            failed += 1
        elif abs(actual - exp_val) < 0.1:
            logger.info(f"  [PASS] {field}: {actual} (期望 {exp_val})")
            passed += 1
        else:
            logger.error(f"  [FAIL] {field}: 期望 {exp_val}, 实际 {actual}")
            failed += 1

    # 验证 ocf_to_profit 计算
    ocf_ratio = metrics.get("ocf_to_profit")
    logger.info(f"  [INFO] ocf_to_profit 计算值: {ocf_ratio}%")

    # 验证 completeness
    comp, level = calc_completeness(metrics)
    logger.info(f"  [INFO] 完整度: {comp*100:.0f}%, 等级: {level}")
    if level == "high":
        logger.info(f"  [PASS] 完整度等级: {level}")
        passed += 1
    else:
        logger.error(f"  [FAIL] 完整度等级: {level} (期望 high)")
        failed += 1

    logger.info(f"Mock 数据验证: {passed} 通过, {failed} 失败\n")
    return failed == 0

# ============================================================
# 主流程
# ============================================================
def main():
    logger.info("=" * 70)
    logger.info("全字段验证 V1.0 - 测试所有输出字段")
    logger.info("=" * 70)

    total_pass = 0
    total_fail = 0

    # ---- 阶段1: Mock 数据验证 ----
    if test_mock_data():
        total_pass += 1
    else:
        total_fail += 1

    # ---- 阶段2: 真实 API 验证 ----
    logger.info("=" * 70)
    logger.info("第2阶段: 真实 API 验证 (10只股票, 所有字段)")
    logger.info("=" * 70)

    token = load_token()

    all_stocks_data = []
    api_success = 0
    api_fail = 0

    for stock in TEST_STOCKS:
        ts_code = stock["ts_code"]
        name = stock["name"]
        logger.info(f"\n--- {ts_code} {name} ---")

        metrics, status = fetch_and_parse(ts_code, name, token)

        if status == "API_EMPTY":
            logger.warning(f"  [SKIP] API 返回为空")
            api_fail += 1
            continue
        elif status == "NO_ANNUAL_BLOCK":
            logger.warning(f"  [SKIP] 未找到年报段落 (API 返回 {len(run_neodata(f'{ts_code} {name} 年报', token))} 字符)")
            api_fail += 1
            continue

        api_success += 1

        # 验证财务字段
        fin_checks, fin_issues = validate_finance_fields(metrics)
        logger.info(f"  财务字段 ({sum(1 for v in fin_checks.values() if v is not None)}/{len(FINANCE_FIELDS)} 有值):")
        for f in FINANCE_FIELDS:
            v = fin_checks.get(f)
            if v is not None:
                if f in ("net_profit", "deducted_profit", "revenue", "ocf_abs"):
                    logger.info(f"    {f} = {v:,.2f}")
                elif f == "ocf_to_profit":
                    logger.info(f"    {f} = {v}%")
                else:
                    logger.info(f"    {f} = {v}")
            else:
                logger.info(f"    {f} = NULL")

        for issue in fin_issues:
            logger.warning(f"  {issue}")
            total_fail += 1

        # 构建评分输入
        stock_data = {
            "ts_code": ts_code, "name": name, "industry_l1": "测试行业",
            **metrics,
        }

        # 评分（用单股票池模拟）
        score_result = calc_score(stock_data, {"测试行业": [stock_data]}, [stock_data])

        # 验证评分字段
        score_checks, score_issues = validate_score_fields(score_result)
        logger.info(f"  评分字段:")
        for f in SCORE_FIELDS:
            logger.info(f"    {f} = {score_checks.get(f)}")
        for issue in score_issues:
            logger.warning(f"  {issue}")
            total_fail += 1

        # 验证元数据字段
        meta_checks, meta_issues = validate_meta_fields(score_result)
        logger.info(f"  元数据字段:")
        for f in META_FIELDS:
            logger.info(f"    {f} = {meta_checks.get(f)}")
        for issue in meta_issues:
            logger.warning(f"  {issue}")
            total_fail += 1

        all_stocks_data.append({
            "ts_code": ts_code, "name": name,
            "metrics": {f: metrics.get(f) for f in FINANCE_FIELDS},
            "scores": {f: score_result.get(f) for f in SCORE_FIELDS},
            "meta": {
                "grade": score_result.get("grade"),
                "confidence": score_result.get("confidence"),
                "completeness": score_result.get("completeness"),
                "completeness_level": score_result.get("completeness_level"),
                "fetch_success": score_result.get("fetch_success"),
                "annual_report_date": score_result.get("annual_report_date"),
                "market_fallback": score_result.get("market_fallback"),
                "ts_code": score_result.get("ts_code"),
                "name": score_result.get("name"),
                "industry_l1": score_result.get("industry_l1"),
            },
        })

        time.sleep(0.3)  # 避免太快

    # ---- 阶段3: 边界情况验证 ----
    logger.info("\n" + "=" * 70)
    logger.info("第3阶段: 边界情况验证")
    logger.info("=" * 70)

    # 3.1 空数据评分
    logger.info("\n  [测试] 空数据评分 (所有字段为 None)")
    empty_stock = {
        "ts_code": "000000.SZ", "name": "测试空", "industry_l1": "测试",
    }
    empty_score = calc_score(empty_stock, {"测试": [empty_stock]}, [empty_stock])
    logger.info(f"    total_score = {empty_score.get('total_score')}")
    logger.info(f"    grade = {empty_score.get('grade')}")
    logger.info(f"    completeness = {empty_score.get('completeness')}")
    logger.info(f"    completeness_level = {empty_score.get('completeness_level')}")
    if empty_score.get("total_score") == 0.0 and empty_score.get("grade") == "E":
        logger.info("    [PASS] 空数据评分正确")
        total_pass += 1
    else:
        logger.error("    [FAIL] 空数据评分异常")
        total_fail += 1

    # 3.2 净利润+现金流双负惩罚
    logger.info("\n  [测试] 净利润+现金流双负惩罚")
    neg_stock = {
        "ts_code": "000001.SZ", "name": "测试负", "industry_l1": "测试",
        "roe": 10.0, "gross_margin": 30.0, "net_margin": 15.0,
        "revenue_yoy": 5.0, "profit_yoy": 8.0, "debt_ratio": 40.0,
        "net_profit": -5e8, "ocf_abs": -3e8,
        "ocf_to_profit": 60.0, "deducted_profit": -4e8,
        "revenue": 1e10, "asset_turnover": 0.5, "ar_turnover": 3.0,
    }
    neg_score = calc_score(neg_stock, {"测试": [neg_stock]}, [neg_stock])
    logger.info(f"    total_score = {neg_score.get('total_score')} (应 <= 15)")
    if neg_score.get("total_score", 999) <= 15.0:
        logger.info("    [PASS] 双负惩罚生效")
        total_pass += 1
    else:
        logger.error("    [FAIL] 双负惩罚未生效")
        total_fail += 1

    # 3.3 完整度惩罚
    logger.info("\n  [测试] 完整度惩罚验证")
    # 高完整度
    high_comp = {
        "roe": 15.0, "gross_margin": 30.0, "net_margin": 15.0,
        "revenue_yoy": 10.0, "profit_yoy": 12.0, "debt_ratio": 40.0,
        "ocf_to_profit": 80.0,
    }
    hc_ratio, hc_level = calc_completeness(high_comp)
    logger.info(f"    7/7 字段: 完整度={hc_ratio:.2f}, 等级={hc_level}")
    if hc_level == "high":
        logger.info("    [PASS] 高完整度判定正确")
        total_pass += 1
    else:
        logger.error("    [FAIL] 高完整度判定错误")
        total_fail += 1

    # 中等完整度
    med_comp = {"roe": 15.0, "gross_margin": 30.0, "net_margin": 15.0, "revenue_yoy": 10.0, "profit_yoy": 12.0}
    mc_ratio, mc_level = calc_completeness(med_comp)
    logger.info(f"    5/7 字段: 完整度={mc_ratio:.2f}, 等级={mc_level}")
    if mc_level == "medium":
        logger.info("    [PASS] 中等完整度判定正确")
        total_pass += 1
    else:
        logger.error("    [FAIL] 中等完整度判定错误")
        total_fail += 1

    # 低完整度
    low_comp = {"roe": 15.0, "gross_margin": 30.0}
    lc_ratio, lc_level = calc_completeness(low_comp)
    logger.info(f"    2/7 字段: 完整度={lc_ratio:.2f}, 等级={lc_level}")
    if lc_level == "low":
        logger.info("    [PASS] 低完整度判定正确")
        total_pass += 1
    else:
        logger.error("    [FAIL] 低完整度判定错误")
        total_fail += 1

    # 超低完整度
    ultra_comp = {"roe": 15.0}
    uc_ratio, uc_level = calc_completeness(ultra_comp)
    logger.info(f"    1/7 字段: 完整度={uc_ratio:.2f}, 等级={uc_level}")
    if uc_level == "ultra_low":
        logger.info("    [PASS] 超低完整度判定正确")
        total_pass += 1
    else:
        logger.error("    [FAIL] 超低完整度判定错误")
        total_fail += 1

    # 3.4 年报段落提取边界
    logger.info("\n  [测试] 年报段落提取边界")

    # 只有年报没有季报
    annual_only = "统计截止日期为20241231的年报\n加权净资产收益率ROE10.0%\n净利润500000000元"
    block = _extract_annual_block(annual_only)
    if block and "加权净资产收益率ROE10.0%" in block:
        logger.info("    [PASS] 仅年报段落提取正确")
        total_pass += 1
    else:
        logger.error("    [FAIL] 仅年报段落提取错误")
        total_fail += 1

    # 年报在开头
    annual_first = "统计截止日期为20241231的年报\nROE10%\n\n统计截止日期为20250331的季报\nROE5%"
    block = _extract_annual_block(annual_first)
    if "ROE10%" in block and "ROE5%" not in block:
        logger.info("    [PASS] 年报+季报混合提取正确")
        total_pass += 1
    else:
        logger.error(f"    [FAIL] 混合提取错误, block={block[:100]}")
        total_fail += 1

    # 无年报
    no_annual = "统计截止日期为20250331的季报\nROE5%"
    block = _extract_annual_block(no_annual)
    if block == "":
        logger.info("    [PASS] 无年报时返回空")
        total_pass += 1
    else:
        logger.error("    [FAIL] 无年报时应返回空")
        total_fail += 1

    # 指定年份提取
    multi_year = "统计截止日期为20231231的年报\nROE8%\n\n统计截止日期为20241231的年报\nROE12%"
    block = _extract_annual_block(multi_year, year=2023)
    if "ROE8%" in block and "ROE12%" not in block:
        logger.info("    [PASS] 指定年份2023提取正确")
        total_pass += 1
    else:
        logger.error(f"    [FAIL] 指定年份提取错误, block={block[:100]}")
        total_fail += 1

    # ---- 阶段4: 输出字段完整性矩阵 ----
    logger.info("\n" + "=" * 70)
    logger.info("第4阶段: 输出字段完整性矩阵")
    logger.info("=" * 70)

    # 表头
    header = f"{'字段':<22} {'类型':<10} {'非空数':<8} {'空数':<8} {'状态'}"
    logger.info(f"\n{header}")
    logger.info("-" * 65)

    field_matrix = {}
    for field in ALL_FIELDS:
        non_null = 0
        null_count = 0
        for sd in all_stocks_data:
            if field in FINANCE_FIELDS:
                val = sd.get("metrics", {}).get(field)
            elif field in SCORE_FIELDS:
                val = sd.get("scores", {}).get(field)
            else:
                val = sd.get("meta", {}).get(field)
            if val is not None:
                non_null += 1
            else:
                null_count += 1
        field_matrix[field] = {"non_null": non_null, "null": null_count}

        # 判断状态
        if non_null == 0 and null_count > 0:
            status = "ALL_NULL"
        elif null_count == 0:
            status = "ALL_OK"
        else:
            status = "PARTIAL"

        # 获取类型
        type_name = "N/A"
        for sd in all_stocks_data:
            if field in FINANCE_FIELDS:
                val = sd.get("metrics", {}).get(field)
            elif field in SCORE_FIELDS:
                val = sd.get("scores", {}).get(field)
            else:
                val = sd.get("meta", {}).get(field)
            if val is not None:
                type_name = type(val).__name__
                break

        logger.info(f"  {field:<20} {type_name:<10} {non_null:<8} {null_count:<8} {status}")

    # ---- 汇总 ----
    logger.info("\n" + "=" * 70)
    logger.info("验证汇总")
    logger.info("=" * 70)
    logger.info(f"  API 成功: {api_success}/{len(TEST_STOCKS)}")
    logger.info(f"  API 失败: {api_fail}/{len(TEST_STOCKS)}")
    logger.info(f"  测试通过: {total_pass}")
    logger.info(f"  测试失败: {total_fail}")

    all_null_fields = [f for f, v in field_matrix.items() if v["non_null"] == 0 and v["null"] > 0]
    if all_null_fields:
        logger.warning(f"\n  [WARNING] 以下字段对所有股票均为 NULL: {all_null_fields}")

    if total_fail == 0:
        logger.info("\n  [RESULT] 全部验证通过!")
    else:
        logger.warning(f"\n  [RESULT] 存在 {total_fail} 个失败项，请检查")

    return total_fail == 0

if __name__ == "__main__":
    ok = main()
    sys.exit(0 if ok else 1)
