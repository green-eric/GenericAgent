#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
基于xuan.txt股票列表的板块分析和市场预期评估
"""

import pandas as pd
from datetime import datetime

def load_xuan_stocks():
    """加载xuan.txt中的股票列表"""
    stocks = []
    with open('d:/Project/QAScorer/xuan.txt', 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line and ':' in line:
                parts = line.split(':')
                if len(parts) == 2:
                    stock_code = parts[0].strip()
                    stock_name = parts[1].strip()
                    if stock_code and stock_name:
                        stocks.append({'股票代码': stock_code, '股票名称': stock_name})
    return stocks

def get_industry_classification():
    """获取行业分类映射"""
    # 简化的行业分类字典（实际应用中应该从更权威的数据源获取）
    industry_map = {
        # 银行保险
        '银行': ['600000', '600015', '600016', '600030', '600036', '601318', '601328', '601398', '601988', '601998'],
        '保险': ['601319', '601601', '601628'],

        # 能源电力
        '石油石化': ['600028', '600348', '600997', '601857', '601808', '601857'],
        '电力': ['600011', '600027', '600025', '600795', '600863', '601991', '601998'],
        '煤炭': ['600123', '600348', '600999', '601001', '601225', '601699'],

        # 通信电子
        '通信设备': ['300308', '300394', '300502', '603220', '603421'],
        '电子元件': ['002138', '002466', '300058', '300433', '603986'],

        # 汽车制造
        '汽车整车': ['000559', '600166', '600686', '601777', '601799'],
        '汽车零部件': ['002035', '002126', '002510', '603169', '603599'],

        # 医药生物
        '化学制药': ['000513', '002001', '002022', '600276', '600529'],
        '生物制品': ['002007', '002030', '300122', '300142', '600271'],
        '医疗器械': ['002022', '300003', '300143', '600085', '600662'],

        # 食品饮料
        '白酒': ['000568', '000799', '002304', '600599', '600596'],
        '啤酒': ['000848', '600600', '600809'],
        '食品加工': ['002014', '002330', '002557', '600597', '600887'],

        # 房地产
        '房地产开发': ['000002', '000667', '600048', '600383', '601588'],

        # 交通运输
        '航空运输': ['600029', '600115', '601111', '601919'],
        '铁路运输': ['601006', '601333', '601390'],
        '港口航运': ['600018', '600017', '600022', '601919'],

        # 钢铁有色
        '钢铁': ['600010', '600022', '600307', '600547', '601005'],
        '有色金属': ['600111', '600362', '600456', '600549', '601600'],

        # 建筑材料
        '水泥': ['600219', '600425', '600585', '600720', '600801'],
        '玻璃陶瓷': ['600586', '600876', '600885'],

        # 化工
        '基础化工': ['600078', '600230', '600309', '600409', '600727'],
        '化学制品': ['002092', '600219', '600598', '600882'],

        # 机械设备
        '通用设备': ['002073', '600312', '600528', '600835', '601717'],
        '专用设备': ['002064', '600359', '600803', '601800', '601898'],

        # 计算机
        '计算机应用': ['002142', '300033', '600570', '600845', '603636'],
        '软件开发': ['002230', '300053', '300369', '600536'],

        # 军工航天
        '航空航天': ['600038', '600316', '600879', '601118', '601989'],
        '国防军工': ['600338', '600760', '600855', '603712', '603985'],

        # 新能源
        '光伏': ['002459', '600151', '600438', '600537', '601211'],
        '风电': ['600290', '600416', '600875', '601212', '601558'],
        '储能': ['300763', '600438', '601211', '601919'],

        # 消费
        '纺织服装': ['002042', '002293', '600148', '600398', '600630'],
        '商贸零售': ['000501', '002770', '600655', '600828', '601010'],
        '酒店餐饮': ['000503', '000796', '600754', '601021'],

        # 传媒娱乐
        '文化传媒': ['000504', '002181', '600637', '600831', '603598'],
        '游戏': ['002174', '002555', '600643', '603444'],

        # 公用事业
        '环保': ['600323', '600874', '600900', '601222', '601368'],
        '水务燃气': ['600168', '600461', '600635', '600903', '600905']
    }
    return industry_map

def analyze_market_expectation(industry):
    """分析行业的市场预期"""
    market_expectations = {
        '新能源': {'level': '强预期', 'reason': '双碳政策+技术突破+需求增长'},
        '光伏': {'level': '强预期', 'reason': '平价上网+技术迭代+全球需求'},
        '风电': {'level': '强预期', 'reason': '海风发展+成本下降+政策支持'},
        '储能': {'level': '极强预期', 'reason': '电网改造+新能源配套+政策驱动'},

        '半导体': {'level': '强预期', 'reason': '国产替代+AI算力+芯片周期复苏'},
        '人工智能': {'level': '极强预期', 'reason': '技术革命+应用落地+资本投入'},
        '生物医药': {'level': '中等预期', 'reason': '创新驱动+人口结构+政策支持'},
        '创新药': {'level': '强预期', 'reason': 'me-better+出海突破+估值修复'},

        '新能源汽车': {'level': '强预期', 'reason': '渗透率提升+技术升级+产业链完善'},
        '智能驾驶': {'level': '强预期', 'reason': 'L2普及+L3试点+传感器放量'},

        '数字经济': {'level': '强预期', 'reason': '数字中国+东数西算+AI赋能'},
        '云计算': {'level': '中等预期', 'reason': '企业上云+混合云+安全需求'},
        '大数据': {'level': '中等预期', 'reason': '数据要素+确权交易+应用场景'},

        '高端制造': {'level': '中等预期', 'reason': '进口替代+产业升级+自主可控'},
        '工业母机': {'level': '中等预期', 'reason': '机床更新+数控化+国产替代'},
        '机器人': {'level': '强预期', 'reason': '自动化+服务机器人+人形机器人'},

        '消费升级': {'level': '弱预期', 'reason': '经济复苏+收入改善+信心恢复'},
        '食品饮料': {'level': '中等预期', 'reason': '必选消费+品牌集中+提价能力'},
        '白酒': {'level': '中等预期', 'reason': '消费分层+头部集中+商务恢复'},

        '金融': {'level': '弱预期', 'reason': '息差压力+地产风险+经济复苏强度'},
        '银行': {'level': '弱预期', 'reason': '资产质量+净息差+拨备计提'},
        '保险': {'level': '弱预期', 'reason': '投资收益+新单增长+权益市场'},

        '传统周期': {'level': '分化预期', 'reason': '供需格局+库存周期+价格弹性'},
        '钢铁': {'level': '分化预期', 'reason': '减产效果+需求复苏+出口变化'},
        '煤炭': {'level': '中等预期', 'reason': '长协比例+进口管控+海外煤价'},
        '有色': {'level': '分化预期', 'reason': '新能源需求+传统需求+美元走势'},

        '建筑建材': {'level': '弱预期', 'reason': '地产竣工+基建投资+原材料价格'},
        '地产链': {'level': '弱预期', 'reason': '销售回暖+政策放松+保交楼进度'},

        '医药健康': {'level': '中等预期', 'reason': '人口老龄化+医保谈判+创新转型'},
        '医疗服务': {'level': '中等预期', 'reason': '诊疗量恢复+集采影响+新技术应用'},

        '其他': {'level': '不确定', 'reason': '需具体分析个股基本面'}
    }
    return market_expectations.get(industry, {'level': '不确定', 'reason': '需要进一步研究'})

def main():
    print("=" * 80)
    print("基于xuan.txt股票列表的板块分析和市场预期评估")
    print(f"分析时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)

    # 加载股票列表
    stocks = load_xuan_stocks()
    print(f"📊 股票列表加载完成: {len(stocks)}只股票")

    # 获取行业分类
    industry_map = get_industry_classification()

    # 分析每只股票的板块归属和市场预期
    analysis_results = []
    industry_stats = {}

    for stock in stocks:
        stock_code = stock['股票代码']
        stock_name = stock['股票名称']

        # 确定行业分类
        industry = '其他'
        for cat, codes in industry_map.items():
            if any(stock_code.startswith(prefix) for prefix in codes):
                industry = cat
                break

        # 获取市场预期分析
        market_expectation = analyze_market_expectation(industry)

        # 统计行业分布
        if industry not in industry_stats:
            industry_stats[industry] = {'count': 0, 'strong_expectation': 0}
        industry_stats[industry]['count'] += 1

        if market_expectation['level'] in ['极强预期', '强预期']:
            industry_stats[industry]['strong_expectation'] += 1

        analysis_results.append({
            '股票代码': stock_code,
            '股票名称': stock_name,
            '所属行业': industry,
            '市场预期等级': market_expectation['level'],
            '预期理由': market_expectation['reason']
        })

    # 生成Excel报告
    df = pd.DataFrame(analysis_results)

    # 保存到桌面
    desktop_path = "C:/Users/green/Desktop"
    excel_file = f"{desktop_path}/xuan_stock_analysis.xlsx"

    with pd.ExcelWriter(excel_file, engine='openpyxl') as writer:
        # 详细分析表
        df.to_excel(writer, sheet_name='股票详细分析', index=False)

        # 行业统计摘要
        industry_summary = []
        for industry, stats in industry_stats.items():
            expectation_rate = stats['strong_expectation'] / stats['count'] * 100 if stats['count'] > 0 else 0
            industry_summary.append({
                '行业': industry,
                '股票数量': stats['count'],
                '强预期股票': stats['strong_expectation'],
                '强预期比例': f"{expectation_rate:.1f}%"
            })

        summary_df = pd.DataFrame(industry_summary)
        summary_df = summary_df.sort_values('股票数量', ascending=False)
        summary_df.to_excel(writer, sheet_name='行业统计摘要', index=False)

        # 重点推荐股票
        strong_expectation_stocks = df[df['市场预期等级'].isin(['极强预期', '强预期'])].copy()
        strong_expectation_stocks = strong_expectation_stocks.sort_values('市场预期等级', key=lambda x: x.map({'极强预期': 0, '强预期': 1, '中等预期': 2}))
        strong_expectation_stocks.to_excel(writer, sheet_name='重点推荐股票', index=False)

    print(f"\n✅ Excel分析报告已生成到桌面:")
    print(f"   {excel_file}")
    print(f"\n📈 分析摘要:")

    # 显示行业分布统计
    print(f"\n行业分布统计:")
    for industry, stats in sorted(industry_stats.items(), key=lambda x: x[1]['count'], reverse=True)[:10]:
        expectation_rate = stats['strong_expectation'] / stats['count'] * 100
        print(f"   {industry}: {stats['count']}只 ({expectation_rate:.1f}% 强预期)")

    # 显示重点推荐行业
    print(f"\n🎯 重点推荐行业:")
    strong_industries = [(k, v) for k, v in industry_stats.items() if v['strong_expectation'] > 0]
    strong_industries.sort(key=lambda x: x[1]['strong_expectation'], reverse=True)

    for industry, stats in strong_industries[:5]:
        if stats['count'] >= 5:  # 至少5只股票的行业才显示
            expectation_rate = stats['strong_expectation'] / stats['count'] * 100
            print(f"   {industry}: {stats['strong_expectation']}/{stats['count']}只股票 ({expectation_rate:.1f}% 强预期)")

    print(f"\n🔍 分析说明:")
    print(f"   • 强预期: 政策利好+基本面改善+技术突破")
    print(f"   • 中等预期: 基本面稳定+估值合理+边际改善")
    print(f"   • 弱预期: 行业周期+竞争格局+盈利压力")
    print(f"   • 不确定: 需结合个股具体情况分析")

    print("\n" + "=" * 80)

if __name__ == "__main__":
    main()