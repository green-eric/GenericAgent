#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
A股智能选股系统 V7.0.0 - 股票字段验证脚本
验证Excel输出与源API数据的一致性
"""

import pandas as pd
import sqlite3
import json
from datetime import datetime
import sys

def load_config():
    """加载配置文件"""
    try:
        with open('industry_map.json', 'r', encoding='utf-8') as f:
            industry_map = json.load(f)
        return industry_map
    except Exception as e:
        print(f"加载配置文件失败: {e}")
        return {}

def get_quarterly_data_from_db(stock_code):
    """从季度缓存数据库获取原始数据"""
    try:
        conn = sqlite3.connect('quarterly_cache.db')
        cursor = conn.cursor()

        # 查询该股票的最新季度数据
        query = """
        SELECT * FROM quarterly_reports
        WHERE ts_code = ?
        ORDER BY end_date DESC, report_type DESC
        LIMIT 4
        """

        cursor.execute(query, (stock_code,))
        rows = cursor.fetchall()

        if not rows:
            return None

        # 获取列名
        columns = [description[0] for description in cursor.description]

        # 转换为字典列表
        data_blocks = []
        for row in rows:
            block = dict(zip(columns, row))
            data_blocks.append(block)

        conn.close()
        return data_blocks

    except Exception as e:
        print(f"数据库查询失败 {stock_code}: {e}")
        return None

def calculate_ttm_from_raw_data(raw_blocks):
    """基于原始数据重新计算TTM值"""
    if not raw_blocks:
        return None

    # 按报告期排序
    sorted_blocks = sorted(raw_blocks, key=lambda x: x.get('end_date', ''), reverse=True)

    # 计算净利润TTM
    profit_sum = 0
    valid_profits = []

    for block in sorted_blocks:
        net_profit = block.get('net_profit', 0)
        if net_profit and net_profit != 0:
            profit_sum += net_profit
            valid_profits.append(net_profit)

    if not valid_profits:
        return None

    # 获取最新季度的净资产
    latest_block = sorted_blocks[0]
    net_assets = latest_block.get('net_assets', 0) or latest_block.get('total_hldr_eqy_exc_min_int', 0)

    # 计算TTM ROE
    roe_ttm = None
    if profit_sum != 0 and net_assets and net_assets > 0:
        roe_ttm = round(profit_sum / net_assets * 100, 2)

    # 计算毛利率TTM
    gross_profit_sum = sum(block.get('gross_profit', 0) or 0 for block in sorted_blocks)
    revenue_sum = sum(block.get('total_revenue', 0) or 0 for block in sorted_blocks)

    gross_margin_ttm = None
    if revenue_sum != 0:
        gross_margin_ttm = round(gross_profit_sum / revenue_sum * 100, 2)

    # 计算净利率TTM
    net_margin_ttm = None
    if revenue_sum != 0:
        net_margin_ttm = round(profit_sum / revenue_sum * 100, 2)

    # 计算经营现金流TTM
    ocf_sum = sum(block.get('net_cash_flows_oper_act', 0) or 0 for block in sorted_blocks)

    result = {
        'roe_ttm': roe_ttm,
        'gross_margin_ttm': gross_margin_ttm,
        'net_margin_ttm': net_margin_ttm,
        'profit_ttm': profit_sum,
        'ocf_ttm': ocf_sum,
        'revenue_ttm': revenue_sum,
        'latest_net_assets': net_assets,
        'valid_quarters': len(valid_profits)
    }

    return result

def verify_stock_fields(excel_file, stock_codes=None):
    """验证指定股票的字段准确性"""
    print("=" * 80)
    print("A股智能选股系统 V7.0.0 - 股票字段验证报告")
    print(f"验证时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)

    # 读取Excel文件
    df = pd.read_excel(excel_file)

    # 如果没有指定股票代码，取前10只
    if stock_codes is None:
        stock_codes = df['股票代码'].head(10).tolist()

    industry_map = load_config()

    verification_results = []

    for i, stock_code in enumerate(stock_codes[:10], 1):
        print(f"\n🔍 验证第{i}只股票: {stock_code}")

        # 查找股票信息
        stock_row = df[df['股票代码'] == stock_code]
        if stock_row.empty:
            print(f"❌ 未找到股票 {stock_code} 在Excel中")
            continue

        stock_info = stock_row.iloc[0]
        stock_name = stock_info['股票名称']

        print(f"   股票名称: {stock_name}")
        print(f"   申万一级行业: {stock_info['申万一级行业']}")

        # 从数据库获取原始季度数据
        raw_data = get_quarterly_data_from_db(stock_code)
        if not raw_data:
            print(f"   ⚠️  未找到 {stock_code} 的季度数据")
            continue

        print(f"   📊 找到 {len(raw_data)} 个季度数据块")

        # 基于原始数据重新计算
        calculated_values = calculate_ttm_from_raw_data(raw_data)

        # 验证各个字段
        verification_result = {
            '股票代码': stock_code,
            '股票名称': stock_name,
            '验证项目': {}
        }

        # 1. 验证ROE TTM
        excel_roe = stock_info.get('ROE(%)(TTM)', None)
        calc_roe = calculated_values.get('roe_ttm', None) if calculated_values else None

        verification_result['验证项目']['ROE_TTM'] = {
            'Excel值': excel_roe,
            '计算值': calc_roe,
            '是否一致': excel_roe == calc_roe if excel_roe is not None and calc_roe is not None else '无法比较',
            '计算过程': f"净利润TTM={calculated_values.get('profit_ttm', 0):,.0f}, 净资产={calculated_values.get('latest_net_assets', 0):,.0f}, ROE={(calculated_values.get('profit_ttm', 0)/calculated_values.get('latest_net_assets', 1)*100):.2f}%"
        }

        # 2. 验证毛利率TTM
        excel_gross = stock_info.get('毛利率(%)(TTM)', None)
        calc_gross = calculated_values.get('gross_margin_ttm', None) if calculated_values else None

        verification_result['验证项目']['毛利率_TTM'] = {
            'Excel值': excel_gross,
            '计算值': calc_gross,
            '是否一致': excel_gross == calc_gross if excel_gross is not None and calc_gross is not None else '无法比较',
            '计算过程': f"毛利TTM={calculated_values.get('revenue_ttm', 0):,.0f}, 收入TTM={calculated_values.get('revenue_ttm', 0):,.0f}, 毛利率={(calculated_values.get('revenue_ttm', 0)/calculated_values.get('revenue_ttm', 1)*100):.2f}%"
        }

        # 3. 验证净利率TTM
        excel_net = stock_info.get('净利率(%)(TTM)', None)
        calc_net = calculated_values.get('net_margin_ttm', None) if calculated_values else None

        verification_result['验证项目']['净利率_TTM'] = {
            'Excel值': excel_net,
            '计算值': calc_net,
            '是否一致': excel_net == calc_net if excel_net is not None and calc_net is not None else '无法比较',
            '计算过程': f"净利润TTM={calculated_values.get('profit_ttm', 0):,.0f}, 收入TTM={calculated_values.get('revenue_ttm', 0):,.0f}, 净利率={(calculated_values.get('profit_ttm', 0)/calculated_values.get('revenue_ttm', 1)*100):.2f}%"
        }

        # 4. 验证净利润TTM
        excel_profit = stock_info.get('净利润(元)(TTM)', None)
        calc_profit = calculated_values.get('profit_ttm', None) if calculated_values else None

        verification_result['验证项目']['净利润_TTM'] = {
            'Excel值': excel_profit,
            '计算值': calc_profit,
            '是否一致': excel_profit == calc_profit if excel_profit is not None and calc_profit is not None else '无法比较',
            '计算过程': f"有效季度数: {calculated_values.get('valid_quarters', 0)}, 净利润总和: {calculated_values.get('profit_ttm', 0):,.0f}"
        }

        # 5. 验证经营现金流TTM
        excel_ocf = stock_info.get('经营现金流(元)(TTM)', None)
        calc_ocf = calculated_values.get('ocf_ttm', None) if calculated_values else None

        verification_result['验证项目']['经营现金流_TTM'] = {
            'Excel值': excel_ocf,
            '计算值': calc_ocf,
            '是否一致': excel_ocf == calc_ocf if excel_ocf is not None and calc_ocf is not None else '无法比较',
            '计算过程': f"现金流TTM: {calculated_values.get('ocf_ttm', 0):,.0f}"
        }

        # 6. 验证成长性指标
        excel_rev_growth = stock_info.get('营收同比(%)(单季)', None)
        excel_profit_growth = stock_info.get('净利润同比(%)(单季)', None)

        verification_result['验证项目']['成长性指标'] = {
            'Excel营收同比': excel_rev_growth,
            'Excel净利润同比': excel_profit_growth,
            '数据来源': '最新单季报',
            '备注': '成长性指标基于最新季度数据'
        }

        # 7. 验证偿债风险
        excel_debt = stock_info.get('资产负债率(%)(单季)', None)
        verification_result['验证项目']['偿债风险'] = {
            'Excel资产负债率': excel_debt,
            '数据来源': '最新季报',
            '备注': '偿债风险指标基于最新季度数据'
        }

        # 8. 验证总分和各维度评分
        total_score = stock_info.get('总分', None)
        profitability = stock_info.get('盈利能力', None)
        growth = stock_info.get('成长性', None)
        cash_quality = stock_info.get('现金流质量', None)
        debt_risk = stock_info.get('偿债风险', None)

        verification_result['验证项目']['综合评分'] = {
            '总分': total_score,
            '盈利能力': profitability,
            '成长性': growth,
            '现金流质量': cash_quality,
            '偿债风险': debt_risk,
            '权重配置': '盈利能力40%+成长性30%+现金流质量20%+偿债风险10%'
        }

        verification_results.append(verification_result)

        # 打印验证结果
        print(f"   📈 ROE(TTM): Excel={excel_roe}%, 计算={calc_roe}% {'✅' if excel_roe == calc_roe else '❌'}")
        print(f"   📈 毛利率(TTM): Excel={excel_gross}%, 计算={calc_gross}% {'✅' if excel_gross == calc_gross else '❌'}")
        print(f"   📈 净利率(TTM): Excel={excel_net}%, 计算={calc_net}% {'✅' if excel_net == calc_net else '❌'}")
        print(f"   💰 净利润(TTM): Excel={excel_profit:,.0f}, 计算={calc_profit:,.0f} {'✅' if excel_profit == calc_profit else '❌'}")
        print(f"   💵 经营现金流(TTM): Excel={excel_ocf:,.0f}, 计算={calc_ocf:,.0f} {'✅' if excel_ocf == calc_ocf else '❌'}")
        print(f"   📊 营收同比: {excel_rev_growth}% (最新单季)")
        print(f"   📊 净利润同比: {excel_profit_growth}% (最新单季)")
        print(f"   🏦 资产负债率: {excel_debt}% (最新单季)")
        print(f"   ⭐ 综合评分: {total_score}分 (盈利能力{profitability}+成长性{growth}+现金流质量{cash_quality}+偿债风险{debt_risk})")

    return verification_results

def generate_test_report(results):
    """生成详细的测试报告"""
    print("\n" + "=" * 80)
    print("📋 详细测试报告摘要")
    print("=" * 80)

    total_stocks = len(results)
    passed_verifications = 0
    total_checks = 0

    for result in results:
        stock_code = result['股票代码']
        print(f"\n📊 {stock_code} 验证结果:")

        for field, check_result in result['验证项目'].items():
            if isinstance(check_result, dict) and '是否一致' in check_result:
                total_checks += 1
                if check_result['是否一致'] == '✅':
                    passed_verifications += 1
                    status = '✅'
                elif check_result['是否一致'] == '❌':
                    status = '❌'
                else:
                    status = '⚠️'
                print(f"   {status} {field}: {check_result['是否一致']}")

    accuracy_rate = passed_verifications / total_checks * 100 if total_checks > 0 else 0
    print(f"\n🎯 总体准确率: {passed_verifications}/{total_checks} ({accuracy_rate:.1f}%)")

    print("\n" + "=" * 80)
    print("✅ 验证完成！")
    print("=" * 80)

    return {
        'total_stocks': total_stocks,
        'total_checks': total_checks,
        'passed_checks': passed_verifications,
        'accuracy_rate': accuracy_rate
    }

if __name__ == "__main__":
    excel_file = "d:/Project/QAScorer/综合评分_20260427_004204.xlsx"

    if not excel_file:
        print("❌ 未找到Excel文件")
        sys.exit(1)

    print(f"开始验证Excel文件: {excel_file}")

    # 执行验证
    results = verify_stock_fields(excel_file)

    # 生成测试报告
    test_summary = generate_test_report(results)

    # 保存详细结果到文件
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_file = f"d:/Project/QAScorer/股票验证报告_{timestamp}.txt"

    with open(report_file, 'w', encoding='utf-8') as f:
        f.write("A股智能选股系统 V7.0.0 - 股票字段验证报告\n")
        f.write("=" * 50 + "\n")
        f.write(f"验证时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"验证文件: {excel_file}\n")
        f.write(f"验证股票数量: {test_summary['total_stocks']}\n")
        f.write(f"总体准确率: {test_summary['accuracy_rate']:.1f}%\n\n")

        for result in results:
            f.write(f"股票: {result['股票代码']} ({result['股票名称']})\n")
            f.write("-" * 30 + "\n")
            for field, check_result in result['验证项目'].items():
                f.write(f"{field}:\n")
                for key, value in check_result.items():
                    if key != '计算过程':
                        f.write(f"  {key}: {value}\n")
                if '计算过程' in check_result:
                    f.write(f"  计算过程: {check_result['计算过程']}\n")
                f.write("\n")

    print(f"\n📄 详细报告已保存到: {report_file}")