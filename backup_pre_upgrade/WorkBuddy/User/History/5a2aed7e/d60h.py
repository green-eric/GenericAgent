#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
A股智能选股分析系统 V2 - 全真实API数据版
===========================================
数据源: NeoData自然语言金融数据搜索API（copilot.tencent.com）
特征:
  - 零随机数据，所有指标均从API实时获取
  - 并行查询（20线程）加速436只股票分析
  - 申万一级行业分类（API真实返回）
  - 行业内百分位评分体系
  - A~E 五级评级
"""

import os
import re
import json
import time
import sys
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

# ---- neodata query.py 路径 ----
QUERY_SCRIPT = Path.home() / ".workbuddy" / "plugins" / "marketplaces" / "cb_teams_marketplace" / "plugins" / "finance-data" / "skills" / "neodata-financial-search" / "scripts" / "query.py"

# ============== 工具函数 ==============

def run_neodata(query_str: str, data_type: str = "api") -> dict:
    """调用neodata API并返回解析后的JSON"""
    import subprocess
    cmd = [
        sys.executable,
        str(QUERY_SCRIPT),
        "--query", query_str,
        "--data-type", data_type,
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=45)
        output = result.stdout.strip()
        # 去除PowerShell的CLIXML噪音
        if "<Objs Version=" in output:
            # 提取JSON部分
            json_match = re.search(r'\{[\s\S]*\}', output)
            if json_match:
                output = json_match.group()
        if not output:
            return {"code": "error", "msg": "empty output"}
        return json.loads(output)
    except subprocess.TimeoutExpired:
        return {"code": "error", "msg": "timeout"}
    except json.JSONDecodeError as e:
        return {"code": "error", "msg": f"json_decode: {e}"}
    except Exception as e:
        return {"code": "error", "msg": str(e)}


def extract_number(text: str, pattern: str) -> float:
    """从文本中用正则提取数值"""
    if not text:
        return None
    match = re.search(pattern, text)
    if match:
        try:
            return float(match.group(1))
        except (ValueError, IndexError):
            return None
    return None


def extract_percent(text: str, key: str) -> float:
    """提取百分比值（返回数值，如 15.5 代表 15.5%）"""
    # 尝试匹配 "key...XX.XX%" 的模式
    patterns = [
        rf'{key}[：:\s]*(-?[\d.]+)\s*%',          # key：XX.XX%
        rf'{key}[为是]*(-?[\d.]+)\s*%',           # key为-15.5%
        rf'{key}\s*[（(]行[业]均值(-?[\d.]+)\s*%',  # key（行业均值...%）
    ]
    for pat in patterns:
        val = extract_number(text, pat)
        if val is not None:
            return val
    return None


# ============== 数据获取 ==============

def fetch_stock_industry(ts_code: str, name: str) -> dict:
    """获取单只股票的申万行业分类"""
    query = f"{ts_code} {name} 所属行业 申万行业分类"
    result = run_neodata(query, "api")
    
    industry_l1 = "未分类"
    industry_l2 = ""
    
    if result.get("code") == "200":
        api_data = result.get("data", {}).get("apiData", {})
        recalls = api_data.get("apiRecall", [])
        for recall in recalls:
            content = recall.get("content", "")
            # 提取一级行业
            m1 = re.search(r'所属一级行业[：:]\s*([^\s，,、]+)', content)
            if m1:
                industry_l1 = m1.group(1).strip()
            # 提取二级行业
            m2 = re.search(r'所属二级行业[：:]\s*([^\s，,、;；]+)', content)
            if m2:
                industry_l2 = m2.group(1).strip()
            if industry_l1 != "未分类":
                break
    
    return {
        "ts_code": ts_code,
        "name": name,
        "industry_l1": industry_l1,
        "industry_l2": industry_l2,
    }


def fetch_stock_finance(ts_code: str, name: str) -> dict:
    """获取单只股票的最新财务指标（年报 + 最新单季报）"""
    query = f"{ts_code} {name} 最新年报财务指标 ROE 毛利率 净利率 资产负债率 营收增长率 净利润增长率 现金流量 经营现金流"
    result = run_neodata(query, "api")
    
    data = {
        "ts_code": ts_code,
        "name": name,
        # 年报指标
        "annual_roe": None,          # 加权净资产收益率 %
        "annual_gross_margin": None, # 销售毛利率 %
        "annual_net_margin": None,   # 销售净利率 %
        "annual_revenue_yoy": None,  # 营收同比增长率 %
        "annual_profit_yoy": None,   # 净利润同比增长率 %
        "annual_ocf_to_profit": None,# 经营现金流/净利润
        "annual_debt_ratio": None,   # 资产负债率 %
        "annual_net_profit": None,   # 净利润(元)
        "annual_deducted_profit": None, # 扣非净利润(元)
        "annual_revenue": None,      # 营业收入(元)
        # 最新单季报指标（用于增长趋势判断）
        "latest_revenue_yoy": None,  # 最新单季营收同比 %
        "latest_profit_yoy": None,   # 最新单季净利润同比 %
        # 运营效率
        "total_asset_turnover": None,# 总资产周转率
        "ar_turnover": None,         # 应收账款周转率
    }
    
    if result.get("code") != "200":
        return data
    
    api_data = result.get("data", {}).get("apiData", {})
    recalls = api_data.get("apiRecall", [])
    
    for recall in recalls:
        content = recall.get("content", "")
        if not content:
            continue
        
        # 判断报告类型
        # 年报: end_date 20251231 且非单季
        # 单季: Q1/Q2/Q3/Q4 单季报
        
        # 分段处理每一段财报数据
        segments = re.split(r'(?:根据|截止日期)', content)
        
        annual_found = False
        for seg in segments:
            # 检测是否为年报数据段
            is_annual = bool(re.search(r'20251231.*年报|年报.*20251231|统计截止日期.*20251231', seg))
            
            if is_annual and not annual_found:
                annual_found = True
                # 提取年报指标
                data["annual_roe"] = extract_percent(seg, r'加权净资产收益率ROE')
                data["annual_gross_margin"] = extract_percent(seg, r'销售毛利率')
                data["annual_net_margin"] = extract_percent(seg, r'销售净利率')
                data["annual_debt_ratio"] = extract_percent(seg, r'资产负债率')
                
                # 营收同比增长
                val = extract_percent(seg, r'营业收入同比增长')
                if val is not None:
                    data["annual_revenue_yoy"] = val
                
                # 净利润同比增长 - 注意可能为负数
                m = re.search(r'净利润同比增长(-?[\d.]+)\s*%', seg)
                if m:
                    data["annual_profit_yoy"] = float(m.group(1))
                
                # 提取绝对值
                m_rev = re.search(r'营业收入([\d.]+)元', seg)
                if m_rev:
                    data["annual_revenue"] = float(m_rev.group(1))
                
                m_np = re.search(r'净利润(-?[\d.]+)元', seg)
                if m_np:
                    data["annual_net_profit"] = float(m_np.group(1))
                
                m_dp = re.search(r'扣非净利润(-?[\d.]+)元', seg)
                if m_dp:
                    data["annual_deducted_profit"] = float(m_dp.group(1))
                
                # 经营现金流/净利润
                m_ocf = re.search(r'经营活动产生的现金流量净额(-?[\d.]+)元', seg)
                if m_ocf and data["annual_net_profit"] and data["annual_net_profit"] != 0:
                    data["annual_ocf_to_profit"] = float(m_ocf.group(1)) / data["annual_net_profit"]
                
                # 总资产周转率
                m_tat = re.search(r'总资产周转率([\d.]+)次', seg)
                if m_tat:
                    data["total_asset_turnover"] = float(m_tat.group(1))
                
                m_ar = re.search(r'应收账款周转率([\d.]+)次', seg)
                if m_ar:
                    data["ar_turnover"] = float(m_ar.group(1))
            
            # 检测最新单季报数据段（用于增长趋势）
            is_latest_q = bool(re.search(r'20260331.*Q1单季', seg) or re.search(r'最新.*单季', seg))
            if is_latest_q:
                val = extract_percent(seg, r'净利润同比增长')
                if val is not None:
                    data["latest_profit_yoy"] = val
                val2 = extract_percent(seg, r'营业收入同比增长')
                if val2 is not None:
                    data["latest_revenue_yoy"] = val2
    
    return data


def fetch_stock_batch(stock_list: list, max_workers: int = 20, fetch_type: str = "finance") -> list:
    """并行批量获取数据"""
    results = []
    fetch_func = fetch_stock_finance if fetch_type == "finance" else fetch_stock_industry
    
    total = len(stock_list)
    done = 0
    failed = 0
    
    print(f"\n[并行获取{fetch_type}数据] 共{total}只股票, {max_workers}线程...")
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {}
        for stock in stock_list:
            ts_code = stock["ts_code"]
            name = stock["name"]
            future = executor.submit(fetch_func, ts_code, name)
            futures[future] = stock
        
        for future in as_completed(futures):
            done += 1
            stock = futures[future]
            try:
                result = future.result()
                results.append(result)
            except Exception as e:
                failed += 1
                results.append({
                    "ts_code": stock["ts_code"],
                    "name": stock["name"],
                    "error": str(e),
                })
            
            if done % 20 == 0 or done == total:
                print(f"  进度: {done}/{total} (失败: {failed})")
    
    print(f"  完成! 成功: {done - failed}, 失败: {failed}")
    return results


# ============== 评分系统 ==============

def percentile_score(value: float, values: list, higher_better: bool = True) -> float:
    """计算百分位评分 (0-100)"""
    if value is None or not values:
        return None
    valid = [v for v in values if v is not None]
    if not valid:
        return None
    
    count_below = sum(1 for v in valid if v < value)
    count_equal = sum(1 for v in valid if v == value)
    percentile = (count_below + 0.5 * count_equal) / len(valid) * 100
    
    if not higher_better:
        percentile = 100 - percentile
    
    return round(percentile, 1)


def calc_score(stock_data: dict, industry_stats: dict) -> dict:
    """计算单只股票的综合评分"""
    
    # --- 获取行业内指标列表用于百分位计算 ---
    ind = stock_data.get("industry_l1", "未分类")
    ind_data = industry_stats.get(ind, {})
    
    roe_list = ind_data.get("roe_list", [])
    gm_list = ind_data.get("gross_margin_list", [])
    nm_list = ind_data.get("net_margin_list", [])
    rev_yoy_list = ind_data.get("revenue_yoy_list", [])
    profit_yoy_list = ind_data.get("profit_yoy_list", [])
    ocf_list = ind_data.get("ocf_ratio_list", [])
    debt_list = ind_data.get("debt_ratio_list", [])
    
    # --- 获取指标值 ---
    roe = stock_data.get("annual_roe")
    gm = stock_data.get("annual_gross_margin")
    nm = stock_data.get("annual_net_margin")
    rev_yoy = stock_data.get("annual_revenue_yoy")
    profit_yoy = stock_data.get("annual_profit_yoy")
    ocf_ratio = stock_data.get("annual_ocf_to_profit")
    debt = stock_data.get("annual_debt_ratio")
    
    # --- 百分位评分 ---
    score_roe = percentile_score(roe, roe_list, higher_better=True) or 50
    score_gm = percentile_score(gm, gm_list, higher_better=True) or 50
    score_nm = percentile_score(nm, nm_list, higher_better=True) or 50
    score_rev_yoy = percentile_score(rev_yoy, rev_yoy_list, higher_better=True) or 50
    score_profit_yoy = percentile_score(profit_yoy, profit_yoy_list, higher_better=True) or 50
    score_ocf = percentile_score(ocf_ratio, ocf_list, higher_better=True) or 50
    score_debt = percentile_score(debt, debt_list, higher_better=False) or 50  # 负债率越低越好
    
    # --- 加权综合评分 ---
    # 权重: 盈利能力35% + 成长性30% + 盈利质量15% + 偿债风险20%
    score_profit = (score_roe * 0.40 + score_gm * 0.30 + score_nm * 0.30)  # 盈利能力内部
    score_growth = (score_rev_yoy * 0.40 + score_profit_yoy * 0.60)        # 成长性内部
    
    total_score = (
        score_profit * 0.35 +
        score_growth * 0.30 +
        score_ocf * 0.15 +
        score_debt * 0.20
    )
    total_score = round(total_score, 2)
    
    # --- 特殊处理：亏损 + 现金流为负 ---
    net_profit = stock_data.get("annual_net_profit")
    ocf = stock_data.get("annual_ocf_to_profit")
    if net_profit is not None and net_profit < 0:
        if ocf is not None and ocf < 0:
            total_score = min(total_score, 10)  # 持续亏损+现金流为负，直接压低
    
    # --- 评级 ---
    if total_score >= 75:
        rating = "A"
    elif total_score >= 55:
        rating = "B"
    elif total_score >= 40:
        rating = "C"
    elif total_score >= 25:
        rating = "D"
    else:
        rating = "E"
    
    return {
        "total_score": total_score,
        "rating": rating,
        "detail": {
            "score_profit": round(score_profit, 1),
            "score_growth": round(score_growth, 1),
            "score_ocf": score_ocf,
            "score_debt": score_debt,
        }
    }


def build_industry_stats(finance_results: list) -> dict:
    """构建行业维度统计（用于百分位计算）"""
    stats = {}
    
    for r in finance_results:
        if "error" in r:
            continue
        ind = r.get("industry_l1", "未分类")
        if ind not in stats:
            stats[ind] = {
                "roe_list": [],
                "gross_margin_list": [],
                "net_margin_list": [],
                "revenue_yoy_list": [],
                "profit_yoy_list": [],
                "ocf_ratio_list": [],
                "debt_ratio_list": [],
            }
        
        s = stats[ind]
        if r.get("annual_roe") is not None:
            s["roe_list"].append(r["annual_roe"])
        if r.get("annual_gross_margin") is not None:
            s["gross_margin_list"].append(r["annual_gross_margin"])
        if r.get("annual_net_margin") is not None:
            s["net_margin_list"].append(r["annual_net_margin"])
        if r.get("annual_revenue_yoy") is not None:
            s["revenue_yoy_list"].append(r["annual_revenue_yoy"])
        if r.get("annual_profit_yoy") is not None:
            s["profit_yoy_list"].append(r["annual_profit_yoy"])
        if r.get("annual_ocf_to_profit") is not None:
            s["ocf_ratio_list"].append(r["annual_ocf_to_profit"])
        if r.get("annual_debt_ratio") is not None:
            s["debt_ratio_list"].append(r["annual_debt_ratio"])
    
    return stats


# ============== 主流程 ==============

def load_stock_list(path: str) -> list:
    """加载股票列表"""
    stocks = []
    with open(path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            parts = line.split(None, 1)
            symbol = parts[0]
            name = parts[1] if len(parts) > 1 else ""
            # 跳过科创板和北交所
            if symbol.startswith('688') or symbol.startswith('430'):
                continue
            suffix = '.SZ' if symbol.startswith(('0', '3')) else '.SH'
            stocks.append({
                "ts_code": symbol + suffix,
                "symbol": symbol,
                "name": name,
            })
    return stocks


def generate_report(results: list, industry_stats: dict) -> str:
    """生成Excel报告"""
    import pandas as pd
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M')
    output_path = f"C:\\Users\\green\\Desktop\\股票业绩评价_{timestamp}_真实API.xlsx"
    
    # 构建DataFrame
    rows = []
    for r in results:
        row = {
            "股票代码": r.get("ts_code", ""),
            "股票名称": r.get("name", ""),
            "一级行业": r.get("industry_l1", "未分类"),
            "二级行业": r.get("industry_l2", ""),
            "加权ROE(%)": r.get("annual_roe"),
            "毛利率(%)": r.get("annual_gross_margin"),
            "净利率(%)": r.get("annual_net_margin"),
            "营收同比(%)": r.get("annual_revenue_yoy"),
            "净利润同比(%)": r.get("annual_profit_yoy"),
            "经营现金流/净利润": r.get("annual_ocf_to_profit"),
            "资产负债率(%)": r.get("annual_debt_ratio"),
            "营业收入(元)": r.get("annual_revenue"),
            "净利润(元)": r.get("annual_net_profit"),
            "扣非净利润(元)": r.get("annual_deducted_profit"),
            "盈利评分": r.get("score_detail", {}).get("score_profit"),
            "成长评分": r.get("score_detail", {}).get("score_growth"),
            "现金流评分": r.get("score_detail", {}).get("score_ocf"),
            "偿债评分": r.get("score_detail", {}).get("score_debt"),
            "总评分": r.get("total_score"),
            "评级": r.get("rating", ""),
        }
        rows.append(row)
    
    df = pd.DataFrame(rows)
    df = df.sort_values("总评分", ascending=False)
    
    # 分级
    df_a = df[df["评级"] == "A"]
    df_b = df[df["评级"] == "B"]
    
    # 行业统计
    industry_dist = df.groupby("一级行业")["总评分"].agg(["count", "mean"]).reset_index()
    industry_dist.columns = ["行业", "股票数量", "平均评分"]
    industry_dist = industry_dist.sort_values("平均评分", ascending=False)
    
    # 评级分布
    rating_dist = df["评级"].value_counts().reset_index()
    rating_dist.columns = ["评级", "数量"]
    rating_dist = rating_dist.sort_values("评级")
    
    with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='综合评价结果', index=False)
        
        if not df_a.empty:
            df_a.to_excel(writer, sheet_name='A级绩优股', index=False)
        
        if not df_b.empty:
            df_b.head(30).to_excel(writer, sheet_name='B级良好股(Top30)', index=False)
        
        industry_dist.to_excel(writer, sheet_name='行业分布统计', index=False)
        
        # 统计概览
        stats_rows = [
            {"项目": "分析股票总数", "数值": len(df)},
            {"项目": "A级(绩优)", "数值": len(df_a)},
            {"项目": "B级(良好)", "数值": len(df_b)},
            {"项目": "C级(一般)", "数值": len(df[df["评级"] == "C"])},
            {"项目": "D级(较差)", "数值": len(df[df["评级"] == "D"])},
            {"项目": "E级(高风险)", "数值": len(df[df["评级"] == "E"])},
            {"项目": "数据来源", "数值": "NeoData真实API"},
            {"项目": "生成时间", "数值": datetime.now().strftime('%Y-%m-%d %H:%M:%S')},
            {"项目": "平均评分", "数值": round(df["总评分"].mean(), 2) if not df.empty else 0},
            {"项目": "最高评分", "数值": round(df["总评分"].max(), 2) if not df.empty else 0},
        ]
        pd.DataFrame(stats_rows).to_excel(writer, sheet_name='统计概览', index=False)
    
    return output_path


def main():
    print("=" * 60)
    print("A股智能选股分析系统 V2 - 全真实API数据版")
    print("=" * 60)
    
    # Step 1: 加载股票列表
    stock_file = "C:\\Users\\green\\Desktop\\gy\\xuan.txt"
    if not os.path.exists(stock_file):
        print(f"股票列表不存在: {stock_file}")
        return
    
    stock_list = load_stock_list(stock_file)
    print(f"加载 {len(stock_list)} 只股票")
    
    # Step 2: 并行获取行业分类
    print("\n--- Phase 1: 获取行业分类 ---")
    industry_results = fetch_stock_batch(stock_list, max_workers=20, fetch_type="industry")
    
    # 构建行业映射
    industry_map = {}
    for r in industry_results:
        industry_map[r["ts_code"]] = {
            "industry_l1": r.get("industry_l1", "未分类"),
            "industry_l2": r.get("industry_l2", ""),
        }
    
    ind_counts = {}
    for v in industry_map.values():
        name = v["industry_l1"]
        ind_counts[name] = ind_counts.get(name, 0) + 1
    print(f"\n行业分布:")
    for name, cnt in sorted(ind_counts.items(), key=lambda x: -x[1]):
        print(f"  {name}: {cnt}只")
    
    # Step 3: 并行获取财务指标
    print("\n--- Phase 2: 获取财务指标 ---")
    finance_results = fetch_stock_batch(stock_list, max_workers=10, fetch_type="finance")
    
    # 合并行业信息到财务数据
    for r in finance_results:
        ts_code = r.get("ts_code", "")
        if ts_code in industry_map:
            r["industry_l1"] = industry_map[ts_code]["industry_l1"]
            r["industry_l2"] = industry_map[ts_code]["industry_l2"]
        else:
            r["industry_l1"] = "未分类"
            r["industry_l2"] = ""
    
    # Step 4: 构建行业统计
    print("\n--- Phase 3: 计算评分 ---")
    industry_stats = build_industry_stats(finance_results)
    print(f"覆盖行业数: {len(industry_stats)}")
    
    # Step 5: 计算综合评分
    for r in finance_results:
        score_result = calc_score(r, industry_stats)
        r["total_score"] = score_result["total_score"]
        r["rating"] = score_result["rating"]
        r["score_detail"] = score_result["detail"]
    
    # Step 6: 生成报告
    print("\n--- Phase 4: 生成报告 ---")
    report_path = generate_report(finance_results, industry_stats)
    
    # 显示结果摘要
    sorted_results = sorted(finance_results, key=lambda x: x.get("total_score", 0), reverse=True)
    
    print(f"\n{'=' * 60}")
    print(f"分析完成! 共 {len(sorted_results)} 只股票")
    print(f"{'=' * 60}")
    
    # A级
    a_stocks = [r for r in sorted_results if r.get("rating") == "A"]
    print(f"\nA级绩优股 ({len(a_stocks)}只):")
    for r in a_stocks[:20]:
        name = r.get("name", "")
        code = r.get("ts_code", "")
        score = r.get("total_score", 0)
        ind = r.get("industry_l1", "")
        roe = r.get("annual_roe", "N/A")
        gm = r.get("annual_gross_margin", "N/A")
        rev = r.get("annual_revenue_yoy", "N/A")
        print(f"  {name}({code}) [{ind}] 评分:{score:.1f} ROE:{roe}% 毛利率:{gm}% 营收增速:{rev}%")
    
    # 评级分布
    print(f"\n评级分布:")
    for rating in ["A", "B", "C", "D", "E"]:
        count = sum(1 for r in sorted_results if r.get("rating") == rating)
        pct = count / len(sorted_results) * 100 if sorted_results else 0
        print(f"  {rating}级: {count}只 ({pct:.1f}%)")
    
    print(f"\nExcel报告: {report_path}")
    
    # 保存中间数据（JSON），方便排查
    json_path = f"C:\\Users\\green\\Desktop\\股票分析数据_{datetime.now().strftime('%Y%m%d_%H%M')}.json"
    # 去掉不方便序列化的内容
    clean_results = []
    for r in sorted_results:
        cr = {k: v for k, v in r.items() if k != "score_detail"}
        cr["score_detail"] = r.get("score_detail", {})
        clean_results.append(cr)
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(clean_results, f, ensure_ascii=False, indent=2)
    print(f"原始数据(JSON): {json_path}")


if __name__ == "__main__":
    main()
