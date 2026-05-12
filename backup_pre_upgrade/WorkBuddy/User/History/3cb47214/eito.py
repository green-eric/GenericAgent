#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
基于xuan.txt股票列表的简化分析脚本
"""

import os
from datetime import datetime

def load_xuan_stocks():
    """加载xuan.txt股票列表"""
    file_path = "d:/Project/QAScorer/xuan.txt"
    if not os.path.exists(file_path):
        print(f"股票列表文件不存在: {file_path}")
        return []

    stocks = []
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line or line.startswith("#"):
                    continue

                parts = line.split()
                if len(parts) < 2:
                    parts = line.split(",")
                if len(parts) < 2:
                    parts = line.split("\t")

                if len(parts) >= 2:
                    code = parts[0].strip()
                    name = parts[1].strip()

                    # 补全市场后缀
                    if "." not in code:
                        code = code + ".SH" if code.startswith("6") else code + ".SZ"

                    stocks.append({"ts_code": code, "name": name})

        print(f"成功加载 {len(stocks)} 只股票")
        return stocks
    except Exception as e:
        print(f"加载股票列表失败: {e}")
        return []

def simple_industry_analysis(stock):
    """简单行业分析"""
    name = stock['name']
    code = stock['ts_code']

    # 基于名称的行业判断
    industry_map = {
        "银行": ["银行", "商行"],
        "食品饮料": ["酒", "饮料", "食品"],
        "医药生物": ["医药", "生物", "制药"],
        "电子": ["电子", "芯片", "半导体"],
        "计算机": ["计算机", "软件", "科技"],
        "汽车": ["汽车", "车辆", "轮胎"],
        "机械设备": ["机械", "设备", "制造"],
        "化工": ["化工", "化学", "材料"],
        "有色金属": ["有色", "金属", "钢铁"],
        "房地产": ["地产", "房产", "建筑"]
    }

    industry = "其他"
    for ind, keywords in industry_map.items():
        for keyword in keywords:
            if keyword in name:
                industry = ind
                break
        if industry != "其他":
            break

    # 根据股票代码前缀判断
    code_prefix = code.split(".")[0][:2]
    prefix_mapping = {
        "60": "机械设备",
        "00": "房地产",
        "30": "医药生物",
        "68": "电子"
    }
    if industry == "其他":
        industry = prefix_mapping.get(code_prefix, "其他")

    return industry

def generate_report():
    """生成分析报告"""
    print("=" * 60)
    print("A股智能选股系统 V7.0.0 - xuan.txt股票分析报告")
    print("=" * 60)

    # 加载股票列表
    stocks = load_xuan_stocks()
    if not stocks:
        return

    print(f"\n分析概览:")
    print(f"   股票代码总数: {len(stocks)}")
    print(f"   分析时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # 分析每只股票
    analysis_results = []
    for i, stock in enumerate(stocks[:20], 1):  # 先分析前20只股票作为示例
        print(f"\n{i}. 分析 {stock['ts_code']} ({stock['name']})...")

        # 简单行业分析
        industry = simple_industry_analysis(stock)
        print(f"   所属行业: {industry}")

        analysis_results.append({
            **stock,
            "industry": industry
        })

    # 生成统计报告
    print("\n" + "=" * 60)
    print("统计分析")
    print("=" * 60)

    # 行业分布统计
    industry_count = {}
    for result in analysis_results:
        ind = result['industry']
        industry_count[ind] = industry_count.get(ind, 0) + 1

    print(f"\n行业分布:")
    for ind, count in sorted(industry_count.items(), key=lambda x: x[1], reverse=True):
        print(f"   {ind}: {count} 只")

    # 保存结果到桌面CSV文件
    save_to_csv(analysis_results, stocks)

def save_to_csv(results, all_stocks):
    """将分析结果保存到CSV文件"""
    try:
        desktop_path = os.path.expanduser("~/Desktop")
        csv_path = os.path.join(desktop_path, f"xuan_stock_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv")

        with open(csv_path, 'w', encoding='utf-8-sig') as f:
            # 写入表头
            f.write("股票代码,股票名称,所属行业,分析时间\n")

            # 写入数据
            for result in results:
                f.write(f"{result['ts_code']},{result['name']},{result['industry']},{datetime.now().strftime('%Y-%m-%d')}\n")

        print(f"\n分析报告已保存到桌面: {os.path.basename(csv_path)}")
        print(f"完整路径: {csv_path}")

    except Exception as e:
        print(f"\nCSV文件生成失败: {e}")

if __name__ == "__main__":
    generate_report()