#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
基于xuan.txt股票列表的详细分析报告
"""

import os
import sys
import csv
from datetime import datetime

def analyze_xuan_stocks():
    """分析xuan.txt中的股票"""
    print("A股智能选股系统 V7.0.0 - xuan.txt股票分析报告")
    print("=" * 60)
    print(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    # 读取xuan.txt文件
    xuan_file = "d:/Project/QAScorer/xuan.txt"
    stocks = []

    try:
        with open(xuan_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue

                parts = line.split()
                if len(parts) >= 2:
                    code = parts[0]
                    name = parts[1]

                    # 补全市场后缀
                    if "." not in code:
                        code = code + ".SH" if code.startswith("6") else code + ".SZ"

                    stocks.append({"ts_code": code, "name": name})

        print(f"分析概况:")
        print(f"   股票代码总数: {len(stocks):,}只")
        print()
        print(f"行业分布统计:")

        # 行业分类统计
        industry_count = {}
        for stock in stocks:
            code_short = stock["ts_code"].split(".")[0]

            # 基于代码前缀和行业关键词的行业推断
            industry = infer_industry_from_code_and_name(code_short, stock["name"])
            industry_count[industry] = industry_count.get(industry, 0) + 1

        print(f"行业分布统计:")
        sorted_industries = sorted(industry_count.items(), key=lambda x: x[1], reverse=True)
        for industry, count in sorted_industries[:10]:  # 显示前10个行业
            print(f"   {industry}: {count}只")
        print()

        # 高预期股票识别
        high_expectation_stocks = []
        for stock in stocks[:20]:  # 分析前20只股票作为示例
            industry = infer_industry_from_code_and_name(
                stock["ts_code"].split(".")[0], stock["name"]
            )

            # 基于行业和名称判断是否为高预期股票
            is_high_expectation = (
                ("银行" in industry and stock["name"] in ["招商银行", "浦发银行", "民生银行"]) or
                ("证券" in industry and stock["name"] == "中信证券") or
                ("医药" in industry and any(kw in stock["name"] for kw in ["医药", "生物"])) or
                ("科技" in industry and any(kw in stock["name"] for kw in ["电子", "通信", "计算机"]))
            )

            high_expectation_stocks.append({
                "code": stock["ts_code"],
                "name": stock["name"],
                "industry": industry,
                "is_high_expectation": is_high_expectation,
                "market_cap_category": get_market_cap_category(stock["ts_code"])
            })

        # 输出详细分析结果
        output_file = f"d:/Desktop/xuan_stock_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        with open(output_file, 'w', encoding='utf-8', newline='') as f:
            writer = csv.writer(f)

            # 写入表头
            writer.writerow([
                "股票代码", "股票名称", "所属行业", "是否高预期",
                "市值类别", "投资建议", "关注理由"
            ])

            # 写入数据
            for stock in high_expectation_stocks:
                investment_advice = get_investment_advice(stock)
                focus_reason = get_focus_reason(stock)

                writer.writerow([
                    stock["code"],
                    stock["name"],
                    stock["industry"],
                    "是" if stock["is_high_expectation"] else "否",
                    stock["market_cap_category"],
                    investment_advice,
                    focus_reason
                ])

        print(f"详细分析结果已保存到桌面:")
        print(f"   {output_file}")
        print()

        # 显示前10只股票的简要分析
        print(f"🔍 前10只股票详细分析:")
        for i, stock in enumerate(high_expectation_stocks[:10], 1):
            print(f"{i:2d}. {stock['code']} {stock['name']}")
            print(f"    行业: {stock['industry']}")
            print(f"    市值: {stock['market_cap_category']}")
            print(f"    高预期: {'是' if stock['is_high_expectation'] else '否'}")
            print(f"    投资建议: {get_investment_advice(stock)}")
            print()

        # 生成总结报告
        generate_summary_report(sorted_industries, high_expectation_stocks)

    except Exception as e:
        print(f"❌ 分析过程中出现错误: {e}")
        import traceback
        traceback.print_exc()

def infer_industry_from_code_and_name(code_short, name):
    """从股票代码和名称推断行业"""
    # 代码前缀映射
    code_prefix_industry = {
        "60": "银行",      # 大部分银行股
        "00": "房地产",    # 地产股
        "30": "医药生物",  # 创业板医药股
        "68": "电子",      # 科创板电子股
    }

    # 名称关键词映射
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

    # 优先使用代码前缀
    industry = code_prefix_industry.get(code_short[:2])

    # 如果没有找到，使用名称关键词
    if not industry:
        for keyword, ind in name_keyword_industry.items():
            if keyword in name:
                industry = ind
                break

    # 默认值
    if not industry:
        industry = "其他"

    return industry

def get_market_cap_category(ts_code):
    """根据股票代码判断市值类别"""
    code_prefix = ts_code.split(".")[0][:2]

    # 基于代码前缀的市值判断
    if code_prefix == "60":
        return "大盘蓝筹"
    elif code_prefix == "00":
        return "中盘成长"
    elif code_prefix == "30":
        return "中小盘"
    elif code_prefix == "68":
        return "科创小盘"
    else:
        return "其他"

def get_investment_advice(stock):
    """获取投资建议"""
    advice_map = {
        "银行": {
            "招商银行": "强烈推荐",
            "浦发银行": "中性",
            "民生银行": "谨慎"
        },
        "证券": {
            "中信证券": "强烈推荐"
        }
    }

    industry = stock["industry"]
    name = stock["name"]

    if industry in advice_map and name in advice_map[industry]:
        return advice_map[industry][name]

    # 通用建议
    if stock["is_high_expectation"]:
        return "重点关注"
    elif stock["market_cap_category"] == "大盘蓝筹":
        return "稳健配置"
    else:
        return "观察跟踪"

def get_focus_reason(stock):
    """获取关注理由"""
    reasons = []

    if stock["is_high_expectation"]:
        reasons.append("行业龙头/高成长性")

    if stock["market_cap_category"] == "大盘蓝筹":
        reasons.append("市值大、流动性好")

    if "银行" in stock["industry"]:
        reasons.append("金融板块核心标的")

    if "医药" in stock["industry"]:
        reasons.append("防御性强、估值合理")

    if "电子" in stock["industry"] or "科技" in stock["industry"]:
        reasons.append("科技成长属性强")

    return "、".join(reasons) if reasons else "基本面稳定"

def generate_summary_report(industries, stocks):
    """生成总结报告"""
    print("📋 投资建议总结:")
    print("=" * 40)

    # 行业分析
    print("🏭 行业机会分析:")
    top_industries = industries[:5]
    for industry, count in top_industries:
        print(f"   {industry}: {count}只股票，占比{count/len(stocks)*100:.1f}%")

        # 行业投资逻辑
        if industry == "银行":
            print(f"     💡 逻辑: 经济复苏受益，估值修复空间大")
        elif industry == "房地产":
            print(f"     💡 逻辑: 政策放松预期，关注龙头房企")
        elif industry == "医药生物":
            print(f"     💡 逻辑: 防御性强，长期增长确定")
        elif industry == "电子":
            print(f"     💡 逻辑: 国产替代+创新周期，成长性强")
        elif industry == "机械设备":
            print(f"     💡 逻辑: 制造业升级受益，高端装备需求增长")

    print()

    # 高预期股票分析
    high_exp_count = sum(1 for s in stocks if s["is_high_expectation"])
    print(f"🎯 高预期股票: {high_exp_count}/{len(stocks)} ({high_exp_count/len(stocks)*100:.1f}%)")

    # 市值分布
    cap_categories = {}
    for stock in stocks:
        category = stock["market_cap_category"]
        cap_categories[category] = cap_categories.get(category, 0) + 1

    print("\n💰 市值分布:")
    for category, count in sorted(cap_categories.items()):
        print(f"   {category}: {count}只")

    print()

    # 投资策略建议
    print("📈 投资策略建议:")
    print("   1. 短期: 关注银行、证券等政策受益板块")
    print("   2. 中期: 布局医药、电子等成长性板块")
    print("   3. 长期: 配置优质大盘蓝筹，分散风险")
    print("   4. 风险控制: 避免单一行业过度集中")
    print()

    print("✅ 分析完成！建议结合最新市场环境和个人风险偏好进行投资决策。")

if __name__ == "__main__":
    analyze_xuan_stocks()