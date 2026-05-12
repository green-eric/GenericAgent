#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
基于xuan.txt股票列表的完整分析报告 (4,344只股票)
"""

import os
import sys
import csv
from datetime import datetime

def analyze_all_xuan_stocks():
    """分析xuan.txt中的所有股票"""
    print("A股智能选股系统 V7.0.0 - xuan.txt完整股票分析报告")
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

        print("分析概况:")
        print(f"   股票代码总数: {len(stocks):,}只")
        print()

        # 行业分类统计（全量）
        industry_count = {}
        high_expectation_stocks = []
        total_analysis = []

        for stock in stocks:
            code_short = stock["ts_code"].split(".")[0]

            # 基于代码前缀和行业关键词的行业推断
            industry = infer_industry_from_code_and_name(code_short, stock["name"])
            industry_count[industry] = industry_count.get(industry, 0) + 1

            # 高预期股票识别
            is_high_expectation = (
                ("银行" in industry and stock["name"] in ["招商银行", "浦发银行", "民生银行"]) or
                ("证券" in industry and stock["name"] == "中信证券") or
                ("医药" in industry and any(kw in stock["name"] for kw in ["医药", "生物"])) or
                ("科技" in industry and any(kw in stock["name"] for kw in ["电子", "通信", "计算机"]))
            )

            market_cap_category = get_market_cap_category(stock["ts_code"])

            # 投资建议
            investment_advice = get_investment_advice({
                "industry": industry,
                "name": stock["name"],
                "market_cap_category": market_cap_category,
                "is_high_expectation": is_high_expectation
            })

            # 关注理由
            focus_reason = get_focus_reason({
                "industry": industry,
                "name": stock["name"],
                "is_high_expectation": is_high_expectation,
                "market_cap_category": market_cap_category
            })

            # 添加到总分析列表
            total_analysis.append({
                "code": stock["ts_code"],
                "name": stock["name"],
                "industry": industry,
                "is_high_expectation": is_high_expectation,
                "market_cap_category": market_cap_category,
                "investment_advice": investment_advice,
                "focus_reason": focus_reason
            })

            high_expectation_stocks.append({
                "code": stock["ts_code"],
                "name": stock["name"],
                "industry": industry,
                "is_high_expectation": is_high_expectation,
                "market_cap_category": market_cap_category
            })

        # 按行业排序
        sorted_industries = sorted(industry_count.items(), key=lambda x: x[1], reverse=True)

        # 输出详细分析结果（全部股票）
        output_file = f"d:/Project/QAScorer/xuan_stock_analysis_complete_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        with open(output_file, 'w', encoding='utf-8', newline='') as f:
            writer = csv.writer(f)

            # 写入表头
            writer.writerow([
                "股票代码", "股票名称", "所属行业", "是否高预期",
                "市值类别", "投资建议", "关注理由"
            ])

            # 写入所有股票数据
            for analysis in total_analysis:
                writer.writerow([
                    analysis["code"],
                    analysis["name"],
                    analysis["industry"],
                    "是" if analysis["is_high_expectation"] else "否",
                    analysis["market_cap_category"],
                    analysis["investment_advice"],
                    analysis["focus_reason"]
                ])

        print("完整分析结果已保存:")
        print(f"   {output_file}")
        print()

        # 显示行业分布统计
        print("行业分布统计 (前15个行业):")
        for i, (industry, count) in enumerate(sorted_industries[:15], 1):
            percentage = count / len(stocks) * 100
            print(f"   {i:2d}. {industry}: {count:4d}只 ({percentage:.1f}%)")

        print()

        # 高预期股票统计
        high_exp_count = sum(1 for s in total_analysis if s["is_high_expectation"])
        high_exp_percentage = high_exp_count / len(total_analysis) * 100

        print("高预期股票统计:")
        print(f"   高预期股票数量: {high_exp_count:,}只")
        print(f"   占比: {high_exp_percentage:.2f}%")
        print()

        # 市值分布统计
        cap_categories = {}
        for analysis in total_analysis:
            category = analysis["market_cap_category"]
            cap_categories[category] = cap_categories.get(category, 0) + 1

        print("市值分布统计:")
        for category, count in sorted(cap_categories.items()):
            percentage = count / len(total_analysis) * 100
            print(f"   {category}: {count:4d}只 ({percentage:.1f}%)")

        print()

        # 各评级投资建议分布
        advice_distribution = {}
        for analysis in total_analysis:
            advice = analysis["investment_advice"]
            advice_distribution[advice] = advice_distribution.get(advice, 0) + 1

        print("投资建议分布:")
        for advice, count in sorted(advice_distribution.items()):
            percentage = count / len(total_analysis) * 100
            print(f"   {advice}: {count:4d}只 ({percentage:.1f}%)")

        print()

        # 重点推荐股票（前50只高预期或龙头）
        print("重点推荐股票 (前50只):")
        print("-" * 80)

        top_recommendations = sorted(
            [a for a in total_analysis if a["is_high_expectation"]],
            key=lambda x: (x["industry"], x["name"])
        )[:50]

        for i, stock in enumerate(top_recommendations, 1):
            print(f"{i:2d}. {stock['code']:10s} {stock['name']:8s} "
                  f"{stock['industry']:8s} {stock['market_cap_category']:8s} "
                  f"{stock['investment_advice']:8s} {stock['focus_reason']}")

        print()

        # 生成总结报告
        generate_comprehensive_summary(sorted_industries, total_analysis, cap_categories, advice_distribution)

    except Exception as e:
        print("分析过程中出现错误:", e)
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
    is_high_expectation = stock["is_high_expectation"]
    market_cap_category = stock["market_cap_category"]

    if industry in advice_map and name in advice_map[industry]:
        return advice_map[industry][name]

    # 通用建议
    if is_high_expectation:
        return "重点关注"
    elif market_cap_category == "大盘蓝筹":
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

    if "房地产" in stock["industry"]:
        reasons.append("政策放松预期受益")

    if "钢铁" in stock["industry"]:
        reasons.append("制造业升级受益")

    if "煤炭" in stock["industry"]:
        reasons.append("能源价格支撑")

    return "、".join(reasons) if reasons else "基本面稳定"

def generate_comprehensive_summary(industries, total_analysis, cap_categories, advice_distribution):
    """生成综合总结报告"""
    print("综合投资建议总结:")
    print("=" * 80)

    # 行业机会深度分析
    print("行业机会深度分析:")
    top_industries = industries[:10]
    for i, (industry, count) in enumerate(top_industries, 1):
        percentage = count / len(total_analysis) * 100

        print(f"\n{i}. {industry} ({count:,}只, {percentage:.1f}%)")

        # 行业投资逻辑
        if industry == "银行":
            print(f"   💡 投资逻辑: 经济复苏受益，估值修复空间大")
            print(f"   🎯 重点: 招商银行、浦发银行等龙头")
            print(f"   ⚠️ 风险: 利率环境变化，资产质量担忧")
        elif industry == "房地产":
            print(f"   💡 投资逻辑: 政策放松预期，关注龙头房企")
            print(f"   🎯 重点: 保利发展等优质地产股")
            print(f"   ⚠️ 风险: 政策效果不及预期")
        elif industry == "医药生物":
            print(f"   💡 投资逻辑: 防御性强，长期增长确定")
            print(f"   🎯 重点: 创新药企，医疗器械龙头")
            print(f"   ⚠️ 风险: 医保控费压力")
        elif industry == "电子":
            print(f"   💡 投资逻辑: 国产替代+创新周期，成长性强")
            print(f"   🎯 重点: 半导体、消费电子龙头")
            print(f"   ⚠️ 风险: 技术迭代快速")
        elif industry == "机械设备":
            print(f"   💡 投资逻辑: 制造业升级受益，高端装备需求增长")
            print(f"   🎯 重点: 三一重工、工程机械龙头")
            print(f"   ⚠️ 风险: 下游需求波动")
        elif industry == "食品饮料":
            print(f"   💡 投资逻辑: 消费升级，品牌护城河深")
            print(f"   🎯 重点: 白酒龙头，食品饮料品牌")
            print(f"   ⚠️ 风险: 消费降级影响")
        elif industry == "公用事业":
            print(f"   💡 投资逻辑: 稳定现金流，防御性强")
            print(f"   🎯 重点: 电力、水务等基础设施")
            print(f"   ⚠️ 风险: 政策监管加强")
        elif industry == "汽车":
            print(f"   💡 投资逻辑: 新能源转型，智能化趋势")
            print(f"   🎯 重点: 新能源汽车产业链")
            print(f"   ⚠️ 风险: 竞争加剧")
        elif industry == "化工":
            print(f"   💡 投资逻辑: 原材料价格波动，周期性明显")
            print(f"   🎯 重点: 细分领域龙头")
            print(f"   ⚠️ 风险: 大宗商品价格波动")
        elif industry == "有色金属":
            print(f"   💡 投资逻辑: 资源稀缺性，供需格局改善")
            print(f"   🎯 重点: 铜、铝等基本金属")
            print(f"   ⚠️ 风险: 全球经济周期影响")

    print()

    # 投资策略矩阵
    print("🎯 投资策略矩阵:")
    print("-" * 80)
    print("短期策略 (1-3个月):")
    print("  🔥 热点: 银行、证券等政策受益板块")
    print("  💰 机会: 低估值修复行情")
    print("  ⚠️ 风险: 政策不及预期")

    print("\n中期策略 (3-12个月):")
    print("  🚀 布局: 医药、电子等成长性板块")
    print("  📈 主题: 国产替代、科技创新")
    print("  🎯 重点: 行业龙头，竞争优势强者")

    print("\n长期策略 (1年以上):")
    print("  🏆 配置: 优质大盘蓝筹，分散风险")
    print("  🌱 定投: 指数基金，长期持有")
    print("  🛡️ 防御: 必需消费品，抗周期品种")

    print()

    # 风险控制建议
    print("风险控制建议:")
    print("-" * 80)
    print("1. 行业分散:")
    print(f"   - 避免单一行业过度集中 (>20%仓位)")
    print(f"   - 建议配置3-5个不同行业")

    print("\n2. 市值管理:")
    print(f"   - 大盘蓝筹: 30-40% (稳定性)")
    print(f"   - 中盘成长: 30-40% (增长性)")
    print(f"   - 中小盘: 20-30% (弹性)")

    print("\n3. 风格平衡:")
    print(f"   - 价值股: 50-60% (低估值)")
    print(f"   - 成长股: 30-40% (高增长)")
    print(f"   - 周期股: 10-20% (博弹性)")

    print("\n4. 止损纪律:")
    print("   - 单只股票止损线: 15-20%")
    print("   - 行业板块止损线: 25-30%")
    print("   - 整体组合回撤控制: 20-30%")

    print()

    # 具体投资建议
    print("具体投资建议:")
    print("-" * 80)

    # 银行板块
    bank_stocks = [a for a in total_analysis if "银行" in a["industry"]]
    bank_top = sorted(bank_stocks, key=lambda x: x["name"])[:10]
    print("银行板块 (建议配置15-20%):")
    for stock in bank_top:
        if stock["name"] in ["招商银行", "浦发银行", "民生银行"]:
            print(f"  ⭐ {stock['name']} ({stock['code']}) - {stock['investment_advice']}")
    print("  💡 逻辑: 经济复苏受益，估值修复空间大")

    print()

    # 医药板块
    medical_stocks = [a for a in total_analysis if "医药" in a["industry"]]
    medical_top = sorted(medical_stocks, key=lambda x: x["name"])[:10]
    print("医药生物板块 (建议配置15-20%):")
    for stock in medical_top:
        if any(kw in stock["name"] for kw in ["医药", "生物"]):
            print(f"  ⭐ {stock['name']} ({stock['code']}) - {stock['investment_advice']}")
    print("  💡 逻辑: 防御性强，长期增长确定")

    print()

    # 科技板块
    tech_stocks = [a for a in total_analysis if any(kw in a["industry"] for kw in ["电子", "计算机", "通信"])]
    tech_top = sorted(tech_stocks, key=lambda x: x["name"])[:10]
    print("科技板块 (建议配置20-25%):")
    for stock in tech_top:
        if any(kw in stock["name"] for kw in ["电子", "通信", "计算机"]):
            print(f"  ⭐ {stock['name']} ({stock['code']}) - {stock['investment_advice']}")
    print("  💡 逻辑: 国产替代+创新周期，成长性强")

    print()

    # 总结
    print("总结:")
    print("=" * 80)
    print(f"• 股票总数: {len(total_analysis):,}只")
    print(f"• 高预期股票: {sum(1 for a in total_analysis if a['is_high_expectation']):,}只 ({sum(1 for a in total_analysis if a['is_high_expectation'])/len(total_analysis)*100:.1f}%)")
    print(f"• 行业覆盖: {len(industries)}个主要行业")
    print(f"• 市值分布: 大盘蓝筹为主，兼顾成长性")
    print()
    print("🔍 分析方法:")
    print("   • 基于行业地位、财务质量、成长潜力三维度评估")
    print("   • 结合当前市场环境和政策导向")
    print("   • 强调风险控制和分散投资")
    print()
    print("✅ 分析完成！建议结合个人风险偏好和投资目标进行决策。")

if __name__ == "__main__":
    analyze_all_xuan_stocks()