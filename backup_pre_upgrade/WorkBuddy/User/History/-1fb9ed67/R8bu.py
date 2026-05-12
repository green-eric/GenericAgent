#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
20只股票9字段详细验证脚本
- 随机取20只股票
- 展示每个单季报段落的提取情况（标识从哪个段落取到的值）
- 验证9个核心字段：ROE(TTM)、毛利率(TTM)、净利率(TTM)、营收同比(单季)、净利润同比(单季)、资产负债率(单季)、OCF/净利润(TTM)、净利润(TTM)、经营现金流(TTM)
"""

import os
import sys
import json
import random
import re
import sqlite3
import logging
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime

# 确保能导入qa_scorer
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from qa_scorer import (
    Config, load_token, fetch_quarterly_data,
    _parse_single_block, _compute_ttm,
    _extract_all_report_sections,
    _parse_num_from_line, parse_num,
    setup_logging
)

logger = logging.getLogger(__name__)


def verify_single_stock(ts_code: str, name: str, token: str) -> Dict:
    """获取单只股票数据并详细展示每个字段来源"""
    
    print(f"\n{'='*80}")
    print(f"股票: {ts_code} {name}")
    print(f"{'='*80}")
    
    # 清除缓存，强制从API获取最新数据
    db_path = Config.QUARTERLY_DB_FILE
    try:
        conn = sqlite3.connect(db_path)
        conn.execute("DELETE FROM quarterly_cache WHERE ts_code = ?", (ts_code,))
        conn.commit()
        conn.close()
    except:
        pass
    
    # 调用API获取数据
    result = fetch_quarterly_data(ts_code, name, token)
    
    content = result.get("content", "")
    ttm_metrics = result.get("ttm_metrics", {})
    latest = result.get("latest_quarterly", {})
    fetch_success = result.get("fetch_success", False)
    quarter_count = result.get("quarter_count", 0)
    latest_quarter = result.get("latest_quarter", "")
    
    if not fetch_success:
        print(f"  ❌ 数据获取失败")
        return {"ts_code": ts_code, "name": name, "success": False}
    
    # 分离段落
    sections = _extract_all_report_sections(content)
    quarterly_sections = [(d, t, txt) for d, t, txt in sections if "季报" in t]
    annual_sections = [(d, t, txt) for d, t, txt in sections if "年报" in t]
    
    print(f"\n📋 报告段落概览 (共{len(sections)}段: {len(quarterly_sections)}个单季报, {len(annual_sections)}个年报)")
    print(f"   最新季报: {latest_quarter}")
    
    # ====== 展示每个单季报段落的提取情况 ======
    print(f"\n{'─'*70}")
    print(f"📊 各单季报段落提取详情:")
    print(f"{'─'*70}")
    
    for i, (q_date, q_type, q_text) in enumerate(quarterly_sections):
        parsed = _parse_single_block(q_text)
        print(f"\n  [{i+1}] {q_date} {q_type}")
        print(f"      {'字段':<20} {'提取值':>20} {'来源行'}")
        print(f"      {'─'*60}")
        
        fields_to_show = [
            ("revenue", "营业总收入", "元"),
            ("operating_cost", "营业成本", "元"),
            ("net_profit", "归母净利润", "元"),
            ("gross_margin", "销售毛利率", "%"),
            ("net_margin", "销售净利率", "%"),
            ("revenue_yoy", "营收同比增长", "%"),
            ("profit_yoy", "净利润同比增长", "%"),
            ("ocf_ratio", "净利润现金含量", "%"),
            ("ocf_abs", "经营现金流净额", "元"),
            ("total_assets", "资产合计", "元"),
            ("total_liabilities", "负债合计", "元"),
            ("net_assets", "净资产", "元"),
            ("debt_ratio", "资产负债率", "%"),
        ]
        
        for field_key, field_name, unit in fields_to_show:
            val = parsed.get(field_key)
            if val is not None:
                if unit == "元" and abs(val) >= 1e8:
                    display = f"{val/1e8:.2f}亿"
                elif unit == "元" and abs(val) >= 1e4:
                    display = f"{val/1e4:.2f}万"
                elif unit == "%":
                    display = f"{val:.2f}%"
                else:
                    display = f"{val:.2f}"
                
                # 找到来源行
                source_line = ""
                for line in q_text.split("\n"):
                    line_s = line.strip()
                    if not line_s:
                        continue
                    if field_key == "revenue" and "营业总收入" in line_s and "同比" not in line_s:
                        source_line = line_s[:60]
                        break
                    elif field_key == "operating_cost" and "营业成本" in line_s and "同比" not in line_s and "营业总成本" not in line_s:
                        source_line = line_s[:60]
                        break
                    elif field_key == "net_profit" and re.match(r"^归母净利润", line_s) and "同比" not in line_s and "扣非" not in line_s:
                        source_line = line_s[:60]
                        break
                    elif field_key == "gross_margin" and "毛利率" in line_s:
                        source_line = line_s[:60]
                        break
                    elif field_key == "net_margin" and "净利率" in line_s:
                        source_line = line_s[:60]
                        break
                    elif field_key == "revenue_yoy" and any(kw in line_s for kw in ["营业收入同比增长", "营收同比增长"]):
                        source_line = line_s[:60]
                        break
                    elif field_key == "profit_yoy" and "净利润同比增长" in line_s:
                        source_line = line_s[:60]
                        break
                    elif field_key == "ocf_ratio" and "净利润现金含量" in line_s:
                        source_line = line_s[:60]
                        break
                    elif field_key == "ocf_abs" and "经营活动产生的现金流量净额" in line_s and "每股" not in line_s:
                        source_line = line_s[:60]
                        break
                    elif field_key == "total_assets" and "资产合计" in line_s and "同比" not in line_s:
                        source_line = line_s[:60]
                        break
                    elif field_key == "total_liabilities" and "负债合计" in line_s and "同比" not in line_s:
                        source_line = line_s[:60]
                        break
                    elif field_key == "net_assets" and any(kw in line_s for kw in ["股东权益合计", "所有者权益合计", "归母净资产"]):
                        source_line = line_s[:60]
                        break
                    elif field_key == "debt_ratio" and "资产负债率" in line_s and "同比" not in line_s:
                        source_line = line_s[:60]
                        break
                
                print(f"      {field_name:<20} {display:>20}  {source_line}")
            else:
                print(f"      {field_name:<20} {'—':>20}  (未提取到)")
    
    # 如果有年报段落也展示
    if annual_sections:
        print(f"\n  📄 年报段落 (共{len(annual_sections)}个):")
        for i, (a_date, a_type, a_text) in enumerate(annual_sections):
            parsed = _parse_single_block(a_text)
            print(f"\n    [{i+1}] {a_date} {a_type}")
            for field_key, field_name, unit in [("revenue_yoy","营收同比增长","%"),("profit_yoy","净利润同比增长","%")]:
                val = parsed.get(field_key)
                if val is not None:
                    print(f"        {field_name}: {val:.2f}%")
    
    # ====== 9个核心字段最终取值汇总 ======
    print(f"\n{'─'*70}")
    print(f"✅ 9个核心字段最终取值汇总:")
    print(f"{'─'*70}")
    
    field_results = {}
    
    # 1. ROE(%)(TTM)
    roe = ttm_metrics.get("roe_ttm")
    field_results["ROE(%)(TTM)"] = roe
    src = f"TTM净利润/最新净资产" if roe is not None else "无数据"
    print(f"  {'ROE(%)(TTM)':<22} = {roe if roe is not None else 'None':>12}  [{src}]")
    
    # 2. 毛利率(%)(TTM)
    gm = ttm_metrics.get("gross_margin_ttm")
    field_results["毛利率(%)(TTM)"] = gm
    src = f"(营收TTM-成本TTM)/营收TTM" if gm is not None else "无数据"
    print(f"  {'毛利率(%)(TTM)':<22} = {gm if gm is not None else 'None':>12}  [{src}]")
    
    # 3. 净利率(%)(TTM)
    nm = ttm_metrics.get("net_margin_ttm")
    field_results["净利率(%)(TTM)"] = nm
    src = f"净利润TTM/营收TTM" if nm is not None else "无数据"
    print(f"  {'净利率(%)(TTM)':<22} = {nm if nm is not None else 'None':>12}  [{src}]")
    
    # 4. 营收同比(%)(单季)
    ry = latest.get("revenue_yoy")
    field_results["营收同比(%)(单季)"] = ry
    src = latest.get("_revenue_yoy_source", "最新单季报" if ry is not None else "所有单季报均无→None")
    print(f"  {'营收同比(%)(单季)':<22} = {ry if ry is not None else 'None':>12}  [来源: {src}]")
    
    # 5. 净利润同比(%)(单季)
    py = latest.get("profit_yoy")
    field_results["净利润同比(%)(单季)"] = py
    src = "最新单季报" if py is not None else "无数据"
    print(f"  {'净利润同比(%)(单季)':<22} = {py if py is not None else 'None':>12}  [{src}]")
    
    # 6. 资产负债率(%)(单季)
    dr = latest.get("debt_ratio")
    field_results["资产负债率(%)(单季)"] = dr
    if dr is not None:
        # 检查是直接提取还是计算
        latest_text = quarterly_sections[0][2] if quarterly_sections else ""
        direct_match = False
        for line in latest_text.split("\n"):
            if "资产负债率" in line and "同比" not in line:
                m = re.search(r"资产负债率[：:\s]*([-+]?\d+\.?\d*)%", line)
                if m:
                    direct_match = True
                    break
        src = "直接提取关键词" if direct_match else "负债合计/资产合计计算"
    else:
        src = "无数据"
    print(f"  {'资产负债率(%)(单季)':<22} = {dr if dr is not None else 'None':>12}  [{src}]")
    
    # 7. OCF/净利润(%)(TTM)
    ocf_r = ttm_metrics.get("ocf_ratio_ttm")
    field_results["OCF/净利润(%)(TTM)"] = ocf_r
    src = "OCF_TTM/净利润TTM" if ocf_r is not None else "无数据"
    print(f"  {'OCF/净利润(%)(TTM)':<22} = {ocf_r if ocf_r is not None else 'None':>12}  [{src}]")
    
    # 8. 净利润(元)(TTM)
    np_ttm = ttm_metrics.get("net_profit_ttm")
    field_results["净利润(元)(TTM)"] = np_ttm
    if np_ttm is not None:
        if abs(np_ttm) >= 1e8:
            display = f"{np_ttm/1e8:.2f}亿"
        else:
            display = f"{np_ttm/1e4:.2f}万"
        src = f"近4季累加 = {display}"
    else:
        src = "无数据"
    print(f"  {'净利润(元)(TTM)':<22} = {np_ttm if np_ttm is not None else 'None':>12}  [{src}]")
    
    # 9. 经营现金流(元)(TTM)
    ocf_abs_ttm = ttm_metrics.get("ocf_abs_ttm")
    field_results["经营现金流(元)(TTM)"] = ocf_abs_ttm
    if ocf_abs_ttm is not None:
        if abs(ocf_abs_ttm) >= 1e8:
            display = f"{ocf_abs_ttm/1e8:.2f}亿"
        else:
            display = f"{ocf_abs_ttm/1e4:.2f}万"
        src = f"近4季直接累加(排除每股) = {display}"
    else:
        src = "无数据"
    print(f"  {'经营现金流(元)(TTM)':<22} = {ocf_abs_ttm if ocf_abs_ttm is not None else 'None':>12}  [{src}]")
    
    # ====== 异常检测 ======
    print(f"\n{'─'*70}")
    print(f"🔍 异常检测:")
    print(f"{'─'*70}")
    
    anomalies = []
    
    if roe is not None and (roe < -100 or roe > 100):
        anomalies.append(f"  ⚠️ ROE(TTM)={roe:.2f}% 超出[-100, 100]范围")
    if gm is not None and (gm < 0 or gm > 100):
        anomalies.append(f"  ⚠️ 毛利率(TTM)={gm:.2f}% 超出[0, 100]范围")
    if nm is not None and (nm < -100 or nm > 100):
        anomalies.append(f"  ⚠️ 净利率(TTM)={nm:.2f}% 超出[-100, 100]范围")
    if ry is not None and (ry < -100 or ry > 1000):
        anomalies.append(f"  ⚠️ 营收同比={ry:.2f}% 超出[-100, 1000]范围")
    if py is not None and (py < -1000 or py > 1000):
        anomalies.append(f"  ⚠️ 净利润同比={py:.2f}% 超出[-1000, 1000]范围")
    if dr is not None and (dr < 0 or dr > 100):
        anomalies.append(f"  ⚠️ 资产负债率={dr:.2f}% 超出[0, 100]范围")
    if ocf_r is not None and (ocf_r < -500 or ocf_r > 500):
        anomalies.append(f"  ⚠️ OCF/净利润={ocf_r:.2f}% 超出[-500, 500]范围")
    if np_ttm is not None and abs(np_ttm) > 1e13:
        anomalies.append(f"  ⚠️ 净利润(TTM)={np_ttm/1e8:.2f}亿 绝对值超过1万亿，可能单位有误")
    if ocf_abs_ttm is not None and abs(ocf_abs_ttm) > 1e13:
        anomalies.append(f"  ⚠️ 经营现金流(TTM)={ocf_abs_ttm/1e8:.2f}亿 绝对值超过1万亿，可能单位有误")
    
    # 检查OCF符号与净利润是否匹配
    if np_ttm is not None and ocf_abs_ttm is not None:
        if np_ttm > 0 and ocf_abs_ttm < 0 and abs(ocf_abs_ttm / np_ttm) > 0.5:
            anomalies.append(f"  ⚠️ 净利润为正但经营现金流为负且幅度较大(OCF/净利润={ocf_r:.1f}%)")
        elif np_ttm < 0 and ocf_abs_ttm > 0 and abs(ocf_abs_ttm / np_ttm) > 0.5:
            anomalies.append(f"  ⚠️ 净利润为负但经营现金流为正且幅度较大(OCF/净利润={ocf_r:.1f}%)")
    
    # 检查经营现金流绝对值是否过小（可能是每股数据误取）
    if ocf_abs_ttm is not None and np_ttm is not None and np_ttm != 0:
        ratio = abs(ocf_abs_ttm / np_ttm)
        if ratio < 0.001 and abs(ocf_abs_ttm) < 1e6:
            anomalies.append(f"  ⚠️ 经营现金流(TTM)={ocf_abs_ttm:.2f}元 绝对值极小，可能误取了每股数据")
    
    if anomalies:
        for a in anomalies:
            print(a)
    else:
        print("  ✅ 无明显异常")
    
    field_results["anomalies"] = anomalies
    field_results["success"] = True
    field_results["ts_code"] = ts_code
    field_results["name"] = name
    
    return field_results


def main():
    setup_logging()
    
    # 读取股票列表
    stock_file = os.path.join(Config.BASE_DIR, "xuan.txt")
    stocks = []
    try:
        with open(stock_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                parts = line.split(",")
                if len(parts) >= 2:
                    stocks.append((parts[0].strip(), parts[1].strip()))
                elif len(parts) == 1:
                    stocks.append((parts[0].strip(), parts[0].strip()))
    except Exception as e:
        print(f"读取股票列表失败: {e}")
        sys.exit(1)
    
    print(f"📈 股票池共 {len(stocks)} 只")
    
    # 随机取20只
    random.seed(42)  # 固定种子以便复现
    sample = random.sample(stocks, min(20, len(stocks)))
    print(f"🎲 随机抽取 {len(sample)} 只股票进行验证 (seed=42)")
    
    # 加载token
    try:
        token = load_token()
    except Exception as e:
        print(f"加载Token失败: {e}")
        sys.exit(1)
    
    # 逐只验证
    all_results = []
    success_count = 0
    anomaly_count = 0
    
    for i, (ts_code, name) in enumerate(sample):
        print(f"\n\n{'#'*80}")
        print(f"# 验证进度: [{i+1}/{len(sample)}]")
        print(f"{'#'*80}")
        
        try:
            result = verify_single_stock(ts_code, name, token)
            all_results.append(result)
            if result.get("success"):
                success_count += 1
            if result.get("anomalies"):
                anomaly_count += 1
        except Exception as e:
            print(f"  ❌ 验证异常: {e}")
            all_results.append({"ts_code": ts_code, "name": name, "success": False, "error": str(e)})
        
        # 避免API限流
        if i < len(sample) - 1:
            import time
            time.sleep(2)
    
    # ====== 汇总报告 ======
    print(f"\n\n{'='*80}")
    print(f"📊 验证汇总报告")
    print(f"{'='*80}")
    print(f"  总验证数: {len(sample)}")
    print(f"  成功获取: {success_count}")
    print(f"  有异常:   {anomaly_count}")
    print(f"  无异常:   {success_count - anomaly_count}")
    
    # 汇总表
    print(f"\n{'─'*100}")
    print(f"{'股票代码':<12} {'名称':<10} {'ROE':>8} {'毛利率':>8} {'净利率':>8} {'营收同比':>10} {'净利同比':>10} {'负债率':>8} {'OCF比':>8} {'异常':>4}")
    print(f"{'─'*100}")
    
    for r in all_results:
        if not r.get("success"):
            print(f"{r['ts_code']:<12} {r.get('name',''):<10} {'获取失败':>50}")
            continue
        
        anomalies_flag = "⚠️" if r.get("anomalies") else "✅"
        roe = r.get("ROE(%)(TTM)")
        gm = r.get("毛利率(%)(TTM)")
        nm = r.get("净利率(%)(TTM)")
        ry = r.get("营收同比(%)(单季)")
        py = r.get("净利润同比(%)(单季)")
        dr = r.get("资产负债率(%)(单季)")
        ocf_r = r.get("OCF/净利润(%)(TTM)")
        
        fmt = lambda v: f"{v:>8.2f}" if v is not None else "     N/A"
        fmt2 = lambda v: f"{v:>10.2f}" if v is not None else "       N/A"
        
        print(f"{r['ts_code']:<12} {r.get('name',''):<10} {fmt(roe)} {fmt(gm)} {fmt(nm)} {fmt2(ry)} {fmt2(py)} {fmt(dr)} {fmt(ocf_r)} {anomalies_flag:>4}")
    
    print(f"{'─'*100}")
    
    # 保存结果
    output_file = os.path.join(Config.BASE_DIR, "verify_20stocks_result.json")
    # 将None值转为可序列化
    serializable = []
    for r in all_results:
        sr = {}
        for k, v in r.items():
            if isinstance(v, float):
                sr[k] = round(v, 4)
            else:
                sr[k] = v
        serializable.append(sr)
    
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(serializable, f, ensure_ascii=False, indent=2)
    print(f"\n📁 详细结果已保存: {output_file}")
    
    return anomaly_count == 0


if __name__ == "__main__":
    all_ok = main()
    if all_ok:
        print("\n✅ 所有股票验证通过，无异常！可以执行全量运行。")
    else:
        print("\n⚠️ 部分股票存在异常，请检查上方详细输出。")
