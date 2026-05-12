#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
xuan.txt 股票列表完整分析报告
生成时间: 2026-04-27
功能: 分析xuan.txt中的4344只股票，进行行业分类和市场预期分析
输出: 桌面Excel报告
"""

import pandas as pd
import numpy as np
from pathlib import Path
import re
from typing import Dict, List, Tuple

def load_stock_list(file_path: str) -> List[str]:
    """加载xuan.txt股票列表"""
    stocks = []
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#'):
                # 提取股票代码
                parts = line.split()
                if parts:
                    code = parts[0]
                    stocks.append(code)
    return stocks

def classify_industry_by_code(stock_code: str) -> str:
    """根据股票代码和行业映射进行分类"""
    # 沪市股票 (6开头)
    if stock_code.startswith('6'):
        sh_prefix = stock_code[:6]

        # 银行类
        if sh_prefix in ['600000', '600015', '600016', '600030', '600050',
                        '600089', '600104', '600348', '600547', '600900']:
            return '金融/银行'
        # 能源类
        elif sh_prefix in ['600011', '600027', '600028', '600029', '600038',
                          '600050', '600188', '600333', '600502', '600900']:
            return '能源/电力'
        # 医药生物
        elif sh_prefix in ['600056', '600062', '600161', '600276', '600518',
                          '600519', '600529', '600557', '600585', '600887']:
            return '医药生物'
        # 汽车制造
        elif sh_prefix in ['600006', '600066', '600166', '600686', '601717']:
            return '汽车制造'
        # 房地产
        elif sh_prefix in ['600048', '600383', '600663', '600675', '600823']:
            return '房地产'
        # 科技电子
        elif sh_prefix in ['600171', '600460', '600536', '600879', '603259']:
            return '科技/电子'
        # 基础材料
        elif sh_prefix in ['600010', '600019', '600058', '600111', '600309']:
            return '基础材料'
        else:
            return '其他'

    # 深市股票 (0开头)
    elif stock_code.startswith('0'):
        sz_prefix = stock_code[:6]

        # 白酒饮料
        if sz_prefix in ['000858', '000568', '000799', '002304', '002507']:
            return '食品饮料'
        # 医药生物
        elif sz_prefix in ['000538', '000513', '000539', '000959', '002022']:
            return '医药生物'
        # 科技电子
        elif sz_prefix in ['002027', '002138', '002415', '002475', '002493']:
            return '科技/电子'
        # 新能源
        elif sz_prefix in ['002594', '002709', '002737', '300750', '300769']:
            return '新能源'
        # 机械设备
        elif sz_prefix in ['002077', '002129', '002371', '002422', '002460']:
            return '机械设备'
        else:
            return '其他'

    # 创业板 (3开头)
    elif stock_code.startswith('3'):
        return '创业板'

    # 科创板 (688开头)
    elif stock_code.startswith('688'):
        return '科创板'

    else:
        return '其他'

def analyze_market_expectation(industry: str, stock_code: str) -> str:
    """基于行业和市场分析判断强预期股票"""
    strong_expectation_industries = {
        '新能源': '强预期 - 政策支持+技术突破',
        '科技/电子': '强预期 - AI+国产替代双驱动',
        '医药生物': '中等预期 - 创新药+医疗器械',
        '汽车制造': '强预期 - 电动化+智能化',
        '半导体': '强预期 - 自主可控+需求爆发',
        '人工智能': '强预期 - 技术革命+应用落地',
        '军工': '中等预期 - 国防现代化+订单饱满',
        '消费': '弱预期 - 消费升级+品牌集中',
        '金融': '弱预期 - 稳增长+估值修复',
        '房地产': '弱预期 - 政策放松+基本面改善',
        '基础材料': '中等预期 - 周期复苏+供需改善',
        '其他': '不确定'
    }

    # 特殊股票判断
    special_cases = {
        '002475': '强预期 - 立讯精密(苹果供应链龙头)',
        '300750': '强预期 - 宁德时代(动力电池王者)',
        '002415': '强预期 - 海康威视(安防AI龙头)',
        '300003': '强预期 - 乐普医疗(心脏支架专家)',
        '000858': '强预期 - 五粮液(高端白酒代表)'
    }

    if stock_code in special_cases:
        return special_cases[stock_code]

    return strong_expectation_industries.get(industry, '不确定')

def generate_analysis_report(stocks: List[str]) -> pd.DataFrame:
    """生成完整的分析报告"""
    print(f"开始分析 {len(stocks)} 只股票...")

    analysis_data = []
    industry_count = {}
    expectation_count = {}

    for i, stock_code in enumerate(stocks, 1):
        if i % 100 == 0:
            print(f"已处理 {i}/{len(stocks)} 只股票")

        # 获取行业分类
        industry = classify_industry_by_code(stock_code)
        industry_count[industry] = industry_count.get(industry, 0) + 1

        # 获取市场预期
        expectation = analyze_market_expectation(industry, stock_code)
        expectation_count[expectation] = expectation_count.get(expectation, 0) + 1

        # 添加数据
        analysis_data.append({
            '股票代码': stock_code,
            '行业分类': industry,
            '市场预期': expectation,
            '预期强度': '强' if '强预期' in expectation else ('中等' if '中等' in expectation else '弱')
        })

    print("分析完成!")
    return pd.DataFrame(analysis_data), industry_count, expectation_count

def create_excel_report(df: pd.DataFrame, industry_count: Dict, expectation_count: Dict):
    """创建Excel报告并保存到桌面"""
    desktop_path = Path.home() / 'Desktop'
    output_file = desktop_path / 'xuan_stock_analysis_report_20260427.xlsx'

    # 创建工作簿
    with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
        # 详细分析表
        df.to_excel(writer, sheet_name='股票详细分析', index=False)

        # 行业分布统计
        industry_df = pd.DataFrame([
            {'行业': k, '股票数量': v, '占比': f"{v/len(df)*100:.1f}%"}
            for k, v in sorted(industry_count.items(), key=lambda x: x[1], reverse=True)
        ])
        industry_df.to_excel(writer, sheet_name='行业分布', index=False)

        # 市场预期统计
        expectation_df = pd.DataFrame([
            {'预期类型': k, '股票数量': v, '占比': f"{v/len(df)*100:.1f}%"}
            for k, v in sorted(expectation_count.items(), key=lambda x: x[1], reverse=True)
        ])
        expectation_df.to_excel(writer, sheet_name='市场预期分布', index=False)

        # 强预期股票列表
        strong_expectation_df = df[df['预期强度'] == '强'].sort_values('股票代码')
        strong_expectation_df.to_excel(writer, sheet_name='强预期股票', index=False)

        # 分析摘要
        summary_data = [
            ['分析项目', '结果'],
            ['总股票数量', len(df)],
            ['覆盖行业数', len(industry_count)],
            ['强预期股票数', len(df[df['预期强度'] == '强'])],
            ['中等预期股票数', len(df[df['预期强度'] == '中等'])],
            ['弱预期股票数', len(df[df['预期强度'] == '弱'])],
            ['分析时间', '2026-04-27'],
            ['数据来源', 'xuan.txt']
        ]
        summary_df = pd.DataFrame(summary_data[1:], columns=summary_data[0])
        summary_df.to_excel(writer, sheet_name='分析摘要', index=False)

    print(f"\n✅ 分析报告已生成: {output_file}")
    print(f"📊 共分析 {len(df)} 只股票")
    print(f"🏆 强预期股票: {len(df[df['预期强度'] == '强'])} 只")
    print(f"📈 中等预期股票: {len(df[df['预期强度'] == '中等'])} 只")
    print(f"📉 弱预期股票: {len(df[df['预期强度'] == '弱'])} 只")

    return output_file

def main():
    """主函数"""
    print("🚀 开始xuan.txt股票列表完整分析...")
    print("=" * 50)

    # 文件路径
    stock_file = r'd:\Project\QAScorer\xuan.txt'

    try:
        # 加载股票列表
        print(f"📥 加载股票列表: {stock_file}")
        stocks = load_stock_list(stock_file)
        print(f"✅ 成功加载 {len(stocks)} 只股票")

        # 生成分析报告
        df, industry_count, expectation_count = generate_analysis_report(stocks)

        # 创建Excel报告
        output_file = create_excel_report(df, industry_count, expectation_count)

        print("\n" + "=" * 50)
        print("🎯 分析结果概览:")
        print(f"   📍 最强预期行业: {max(industry_count.items(), key=lambda x: x[1])}")
        print(f"   🔥 最多强预期: {max(expectation_count.items(), key=lambda x: x[1])}")

        print("\n📋 建议关注方向:")
        strong_industries = [k for k, v in industry_count.items() if v > 100]
        for industry in strong_industries:
            strong_stocks = len(df[(df['行业分类'] == industry) & (df['预期强度'] == '强')])
            print(f"   • {industry}: {strong_stocks} 只强预期股票")

        print(f"\n💡 报告位置: {output_file}")

    except Exception as e:
        print(f"❌ 分析过程中出现错误: {e}")
        raise

if __name__ == "__main__":
    main()