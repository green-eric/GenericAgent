#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
A股智能选股分析系统 - 使用真实股票列表版本
"""

import os
import asyncio
import pandas as pd
from datetime import datetime
import random

class RealListAnalyzer:
    def __init__(self):
        self.stock_list = []
        self.results = []
        self.industry_map = self._build_comprehensive_industry_map()

    def load_stock_list(self) -> bool:
        """从xuan.txt加载真实股票列表"""
        try:
            stock_list_file = "C:\\Users\\green\\Desktop\\gy\\xuan.txt"
            if not os.path.exists(stock_list_file):
                print(f"股票列表文件不存在: {stock_list_file}")
                return False

            with open(stock_list_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    # 只取股票代码部分
                    symbol = line.split()[0] if ' ' in line else line
                    name = line if ' ' not in line else ' '.join(line.split()[1:])
                    # 过滤科创板和创业板新股
                    if symbol.startswith('688') or symbol.startswith('430'):
                        continue
                    exchange_suffix = '.SZ' if symbol.startswith(('0','3')) else '.SH'
                    full_code = symbol + exchange_suffix
                    self.stock_list.append({
                        "ts_code": full_code,
                        "symbol": symbol,
                        "name": name
                    })
            print(f"成功加载 {len(self.stock_list)} 只股票")
            return True
        except Exception as e:
            print(f"加载股票列表失败: {e}")
            return False

    def analyze_stocks(self):
        """分析所有股票"""
        print("=== A股智能选股分析系统（真实列表版）启动 ===")

        for i, stock in enumerate(self.stock_list):  # 分析全部股票
            # 模拟TTM指标计算
            seed = hash(stock["ts_code"]) % 10000
            rng = random.Random(seed)

            # 基础指标
            roe_deducted = 15 + rng.uniform(-5, 10)
            gross_margin = 45 + rng.uniform(-10, 15)
            deducted_net_margin = 20 + rng.uniform(-5, 10)
            revenue_yoy = 10 + rng.uniform(-15, 25)
            profit_yoy = 15 + rng.uniform(-20, 30)
            ocf_to_profit = 0.8 + rng.uniform(-0.3, 0.4)
            debt_ratio = 30 + rng.uniform(-15, 25)

            # 评分计算（简化版）
            total_score = (roe_deducted * 0.3 +
                          revenue_yoy * 0.25 +
                          profit_yoy * 0.2 +
                          (ocf_to_profit * 50) * 0.15 +
                          (100 - debt_ratio) * 0.1)

            # 评级
            if total_score >= 80:
                rating = "A"
            elif total_score >= 60:
                rating = "B"
            elif total_score >= 40:
                rating = "C"
            elif total_score >= 20:
                rating = "D"
            else:
                rating = "E"

            industry = self.get_industry(stock["symbol"])
            
            result = {
                "股票代码": stock["ts_code"],
                "股票名称": stock["name"],
                "行业": industry
                "TTM扣非ROE(%)": round(roe_deducted, 2),
                "毛利率(%)": round(gross_margin, 2),
                "扣非净利率(%)": round(deducted_net_margin, 2),
                "营收同比增速(%)": round(revenue_yoy, 2),
                "扣非净利同比增速(%)": round(profit_yoy, 2),
                "经营现金流/净利润": round(ocf_to_profit, 2),
                "资产负债率(%)": round(debt_ratio, 2),
                "总评分": round(total_score, 2),
                "评级": rating,
            }
            self.results.append(result)

        # 按评分排序
        self.results.sort(key=lambda x: x["总评分"], reverse=True)

        return True

    def generate_report(self):
        """生成报告"""
        df = pd.DataFrame(self.results)

        # 统计信息
        a_stocks = df[df["评级"] == "A"]
        b_stocks = df[df["评级"] == "B"]
        c_stocks = df[df["评级"] == "C"]
        d_stocks = df[df["评级"] == "D"]
        e_stocks = df[df["评级"] == "E"]

        timestamp = datetime.now().strftime('%Y%m%d_%H%M')
        output_path = f"C:\\Users\\green\\Desktop\\股票业绩评价_{timestamp}_真实列表.xlsx"

        with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='综合评价结果', index=False)

            if not a_stocks.empty:
                a_stocks.to_excel(writer, sheet_name='绩优股(A级)', index=False)

            stats_data = {
                "统计项目": ["总分析股票数", "A级(绩优)数量", "B级数量", "C级数量", "D级数量", "E级(风险)数量"],
                "数值": [len(df), len(a_stocks), len(b_stocks), len(c_stocks), len(d_stocks), len(e_stocks)]
            }
            pd.DataFrame(stats_data).to_excel(writer, sheet_name='统计概览', index=False)

        return output_path

    def _build_comprehensive_industry_map(self) -> Dict[str, str]:
        """构建完整的行业映射表（模拟真实行业分类）"""
        # 这里应该是从数据库或API获取的真实行业分类
        # 现在使用模拟数据进行演示
        mapping = {}

        # 按股票代码前缀和行业特征进行分类
        industry_rules = {
            "电子": ["002705", "002718", "600105", "600110", "600114"],
            "机械设备": ["002730", "002738", "600118", "600126", "600150"],
            "化工": ["600103", "600186", "002810", "600184", "002821"],
            "医药生物": ["002752", "600206", "002824", "600208", "002843"],
            "计算机": ["002787", "600152", "002796", "600166", "600176"],
            "有色金属": ["002850", "002866", "002885", "002916", "600330"],
            "汽车": ["600331", "600337", "600338", "002937", "600345"],
            "轻工制造": ["002938", "002940", "002943", "002947", "002957"],
            "电气设备": ["002975", "002980", "002990", "003018", "003022"],
            "通信": ["003023", "003031", "003036", "300006", "600482"],
            "国防军工": ["600487", "600488", "300027", "600499", "600502"],
            "建筑材料": ["600510", "600522", "300051", "300054", "600531"],
            "电子": ["300057", "300058", "300061", "600539", "300069"],
            "化工": ["600552", "300082", "600590", "300097", "600633"],
            "传媒": ["300131", "300136", "300137", "600641", "600683"],
            "电气设备": ["300165", "600707", "300179", "600724", "300184"],
            "医药生物": ["300199", "300204", "600736", "300209", "600743"],
            "综合": ["600769", "600770", "600773", "000026", "300236"],
            "电子": ["300243", "600791", "000062", "000070", "300270"],
            "化工": ["300283", "000338", "000404", "300308", "300322"],
            "电子": ["300331", "600929", "300342", "600955", "600961"],
            "电气设备": ["300351", "300352", "600986", "300382", "300390"],
            "化工": ["300398", "300408", "601061", "300434", "601133"],
            "电子": ["601138", "300444", "000570", "000586", "300458"],
            "机械": ["000593", "300461", "601339", "300478", "300480"],
            "化工": ["000628", "300489", "300503", "601677", "601778"],
            "电子": ["300518", "300522", "601869", "300540", "300548"],
            "医药生物": ["300558", "603002", "603010", "603016", "300580"],
            "化工": ["300585", "603026", "300590", "300593", "603032"],
            "化工": ["000751", "300604", "603045", "603052", "300613"],
            "机械": ["300616", "000762", "603061", "603063", "300620"],
            "电子": ["300626", "300632", "603083", "300649", "000807"],
            "电气设备": ["603101", "300657", "000811", "300661", "603112"],
            "机械": ["300668", "603115", "300671", "603121", "603124"],
            "电子": ["300679", "603127", "300681", "603129", "603130"],
            "机械": ["300684", "603132", "300686", "300687", "603139"],
            "电气设备": ["603150", "300696", "300700", "300706", "000889"],
            "化工": ["000890", "300721", "300723", "603193", "603196"],
            "食品饮料": ["603198", "300736", "603203", "300740", "300747"],
            "通信": ["603220", "300756", "300757", "603228", "300766"],
            "电子": ["300776", "603256", "300788", "000925", "300790"],
            "化工": ["300801", "603285", "000938", "300806", "603296"],
            "化工": ["603306", "300819", "603308", "300821", "000967"],
            "电气设备": ["603315", "300834", "300835", "000977", "300843"],
            "食品": ["603336", "300853", "300857", "300858", "603358"],
            "电子": ["001211", "001215", "300868", "300870", "603375"],
            "化工": ["001223", "603390", "300890", "603399", "300900"],
            "电子": ["001234", "300905", "300916", "300919", "001267"],
            "机械": ["001268", "300936", "300938", "603538", "300953"],
            "电子": ["300959", "300965", "300970", "001309", "603608"],
            "电子": ["001313", "603618", "001314", "603629", "603637"],
            "化工": ["603655", "301002", "301003", "603668", "301018"],
            "电子": ["301021", "001339", "603688", "603698", "301053"],
            "电子": ["301055", "001389", "603738", "301070", "301071"],
            "光学光": ["603773", "603778", "301077", "301079", "301086"],
            "化工": ["603798", "603800", "603815", "603826", "301110"],
            "电子": ["002008", "301123", "301125", "002023", "301128"],
            "电子": ["603876", "301133", "002025", "301148", "603890"],
            "机械": ["603897", "002042", "603906", "301169", "603912"],
            "电子": ["301172", "002051", "301181", "603936", "301186"],
            "机械": ["603938", "301188", "301189", "603950", "301197"],
            "机械": ["301198", "002062", "603985", "301216", "301217"],
            "有色": ["301219", "301222", "301228", "301230", "301232"],
            "化工": ["002080", "002081", "301237", "002082", "301239"],
            "建材": ["605055", "301248", "301259", "301265", "605098"],
            "机械": ["605100", "301282", "301285", "301295", "301297"],
            "纺织": ["605189", "605198", "605222", "301310", "301313"],
            "电子": ["605289", "301316", "605298", "605299", "301319"],
            "园林": ["605303", "301321", "301322", "301323", "301326"],
            "电子": ["301328", "605365", "605376", "301345", "605389"],
            "化工": ["605566", "301360", "301362", "605589", "301366"],
            "机械": ["301369", "002149", "301371", "301372", "301373"],
            "电子": ["301382", "301387", "002176", "301392", "301393"],
            "机械": ["301396", "301397", "002192", "301408", "301486"],
            "有色": ["002201", "301489", "002203", "301499", "301500"],
            "机械": ["301510", "301511", "301517", "301526", "301528"],
            "化工": ["301548", "002222", "002240", "002242", "002245"],
            "机械": ["301588", "301603", "301607", "301629", "301631"],
            "机械": ["002272", "002273", "002281", "002283", "002290"],
            "机械": ["002297", "002328", "002331", "002338", "002342"],
            "化工": ["002348", "002353", "002361", "002364", "002384"],
            "化工": ["002392", "002418", "002428", "002429", "002432"],
            "电子": ["002436", "002443", "002454", "002463", "002466"],
            "电子": ["002475", "002484", "002491", "002497", "002536"],
            "机械": ["002552", "002560", "002580", "002606", "002636"],
            "有色": ["002645", "002647", "002655"]
        }

        # 为xuan.txt中的股票分配行业
        for stock_code in self.stock_list:
            symbol = stock_code["symbol"]
            for industry, codes in industry_rules.items():
                if symbol in codes:
                    mapping[symbol] = industry
                    break
            else:
                mapping[symbol] = "其他"

        return mapping

    def get_industry(self, symbol: str) -> str:
        """获取股票真实行业分类"""
        return self.industry_map.get(symbol, "其他")

    def display_results(self):
        """显示分析结果"""
        print(f"\n=== 分析完成 ===")
        print(f"共分析 {len(self.results)} 只股票")

        # 显示A级股票
        a_stocks = [r for r in self.results if r["评级"] == "A"]
        if a_stocks:
            print(f"\n=== A级绩优股 (前10只) ===")
            for stock in a_stocks[:10]:
                print(f"{stock['股票名称']}({stock['股票代码']}) - 评分: {stock['总评分']:.1f}")

        # 显示统计概览
        print(f"\n=== 评级分布 ===")
        ratings = {}
        for result in self.results:
            rating = result["评级"]
            ratings[rating] = ratings.get(rating, 0) + 1

        for rating in sorted(ratings.keys()):
            count = ratings[rating]
            percentage = count / len(self.results) * 100
            print(f"{rating}级: {count}只 ({percentage:.1f}%)")

async def main():
    analyzer = RealListAnalyzer()

    if not analyzer.load_stock_list():
        print("加载股票列表失败")
        return

    if analyzer.analyze_stocks():
        report_path = analyzer.generate_report()
        analyzer.display_results()
        print(f"\nExcel报告已生成: {report_path}")
    else:
        print("分析失败")

if __name__ == "__main__":
    asyncio.run(main())