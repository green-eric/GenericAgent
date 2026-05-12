#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""验证 5 只随机股票的真实 API 数据获取与解析"""
import sys, json, re, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from stock_analyzer import (
    load_token, run_neodata, _extract_annual_block,
    parse_financial_all, parse_num, _parse_num_from_line,
    fetch_stock_finance, setup_logging, Config
)
import requests as req_lib
from requests.adapters import HTTPAdapter

logger = setup_logging()

STOCKS = [
    ("300012.SZ", "华测检测"),
    ("002938.SZ", "鹏鼎控股"),
    ("600580.SH", "卧龙电驱"),
    ("605377.SH", "华旺科技"),
    ("002611.SZ", "东方精工"),
]

def verify_stock(ts_code, name, token, session):
    logger.info(f"\n{'='*60}")
    logger.info(f"验证: {ts_code} {name}")
    logger.info(f"{'='*60}")

    result = fetch_stock_finance(ts_code, name, token, session)
    metrics = result.get("metrics", {})
    content = result.get("content", "")
    report_date = result.get("report_date", "")
    success = result.get("fetch_success", False)

    logger.info(f"API 获取成功: {success}")
    logger.info(f"年报日期: {report_date}")
    logger.info(f"内容长度: {len(content)} 字符")

    if not success:
        logger.warning("  -> 获取失败，跳过指标解析")
        return {"ts_code": ts_code, "name": name, "success": False}

    # 打印年报段落前 500 字符
    block = _extract_annual_block(content)
    logger.info(f"年报段落长度: {len(block)} 字符")
    if block:
        logger.info(f"年报段落预览:\n{block[:500]}...")

    # 打印各项指标
    fields = [
        ("roe", "ROE(%)"),
        ("gross_margin", "毛利率(%)"),
        ("net_margin", "净利率(%)"),
        ("revenue_yoy", "营收同比(%)"),
        ("profit_yoy", "净利润同比(%)"),
        ("debt_ratio", "资产负债率(%)"),
        ("net_profit", "净利润(元)"),
        ("deducted_profit", "扣非净利润(元)"),
        ("revenue", "营业总收入(元)"),
        ("ocf_abs", "经营现金流(元)"),
        ("ocf_to_profit", "OCF/净利润(%)"),
        ("asset_turnover", "总资产周转率"),
        ("ar_turnover", "应收账款周转率"),
    ]
    logger.info("--- 财务指标 ---")
    for key, label in fields:
        val = metrics.get(key)
        if val is not None:
            if key in ("net_profit", "deducted_profit", "revenue", "ocf_abs"):
                logger.info(f"  {label}: {val:,.0f}")
            elif key in ("roe", "gross_margin", "net_margin", "revenue_yoy", "profit_yoy", "debt_ratio"):
                logger.info(f"  {label}: {val:.2f}%")
            else:
                logger.info(f"  {label}: {val}")
        else:
            logger.warning(f"  {label}: [None]")

    return {"ts_code": ts_code, "name": name, "success": True, "metrics": metrics, "report_date": report_date}


def main():
    logger.info("=" * 60)
    logger.info("5 只股票真实 API 验证")
    logger.info("=" * 60)

    token = load_token()
    adapter = HTTPAdapter(pool_connections=5, pool_maxsize=5, max_retries=2)
    session = req_lib.Session()
    session.mount("https://", adapter)
    session.mount("http://", adapter)

    results = []
    for ts_code, name in STOCKS:
        try:
            r = verify_stock(ts_code, name, token, session)
            results.append(r)
        except Exception as e:
            logger.error(f"验证异常 {ts_code} {name}: {e}")
            results.append({"ts_code": ts_code, "name": name, "success": False, "error": str(e)})

    session.close()

    # 汇总
    logger.info(f"\n{'='*60}")
    logger.info("验证汇总")
    logger.info(f"{'='*60}")
    success_count = sum(1 for r in results if r.get("success"))
    logger.info(f"成功: {success_count}/{len(STOCKS)}")

    for r in results:
        status = "[OK]" if r.get("success") else "[FAIL]"
        metrics = r.get("metrics", {})
        roe = metrics.get("roe", "N/A")
        profit = metrics.get("net_profit")
        profit_str = f"{profit:,.0f}" if profit else "N/A"
        logger.info(f"  {status} {r['ts_code']} {r['name']}: ROE={roe}, 净利润={profit_str}")

    # 保存验证结果
    import json as j
    from datetime import datetime
    out_file = os.path.join(Config.OUTPUT_DIR, f"验证结果_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
    with open(out_file, "w", encoding="utf-8") as f:
        # 序列化时处理大数字
        class Encoder(j.JSONEncoder):
            def default(self, o):
                if isinstance(o, float):
                    return round(o, 4)
                return super().default(o)
        j.dump(results, f, ensure_ascii=False, indent=2, cls=Encoder)
    logger.info(f"验证结果已保存: {out_file}")

if __name__ == "__main__":
    main()
