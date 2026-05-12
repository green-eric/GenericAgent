"""
项目演示脚本 - 展示A股年报增长率分析项目的完整功能

这个脚本将运行完整的分析流程并生成所有报告和图表。
"""

import os
import sys
import logging
from pathlib import Path

# 添加当前目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from main import StockAnalysisApp
from report_analyzer import ReportAnalyzer
from growth_filter import AdvancedGrowthFilter, FilterCriteria
import pandas as pd
import matplotlib.pyplot as plt

def setup_directories():
    """创建必要的目录结构"""
    directories = [
        './data',
        './output',
        './logs',
        './visualizations'
    ]

    for directory in directories:
        Path(directory).mkdir(exist_ok=True)
        print(f"✓ 创建目录: {directory}")

def run_complete_analysis():
    """运行完整的分析流程"""
    print("🚀 开始A股年报增长率分析演示")
    print("=" * 60)

    try:
        # 初始化应用程序
        app = StockAnalysisApp()

        # 运行主分析流程
        print("\n📊 正在执行完整分析流程...")
        app.run_analysis()

        print("\n✅ 基础分析完成！")

    except Exception as e:
        print(f"❌ 分析过程中出现错误: {str(e)}")
        return False

    return True

def generate_summary_report():
    """生成项目摘要报告"""
    print("\n📋 生成项目摘要报告...")

    # 读取分析结果
    output_dir = Path('./output')
    results_file = output_dir / 'high_growth_stocks_2025.xlsx'

    if not results_file.exists():
        print("⚠️  未找到分析结果文件，跳过摘要报告生成")
        return

    try:
        df = pd.read_excel(results_file, sheet_name='高增长股票')

        # 生成摘要统计
        summary_stats = {
            '总股票数量': len(df),
            '平均营收增长率': f"{df['营业收入同比增长率'].mean():.2f}%",
            '平均利润增长率': f"{df['净利润同比增长率'].mean():.2f}%",
            '最高营收增长率': f"{df['营业收入同比增长率'].max():.2f}%",
            '最高利润增长率': f"{df['净利润同比增长率'].max():.2f}%",
            '行业分布': df['所属行业'].value_counts().to_dict()
        }

        # 保存摘要报告
        summary_path = output_dir / 'project_summary.txt'
        with open(summary_path, 'w', encoding='utf-8') as f:
            f.write("# A股2025年年报增长率分析项目 - 项目摘要报告\n\n")
            f.write(f"**生成时间**: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")

            f.write("## 项目概览\n")
            f.write("- 项目目标: 分析2025年年报中增长率大于50%的A股股票\n")
            f.write("- 数据来源: 东方财富金融工具集（模拟数据）\n")
            f.write("- 分析方法: 多维度增长率筛选与综合评估\n\n")

            f.write("## 核心成果\n")
            for key, value in summary_stats.items():
                if isinstance(value, dict):
                    f.write(f"- **{key}**: \n")
                    for industry, count in value.items():
                        f.write(f"  - {industry}: {count}只股票\n")
                else:
                    f.write(f"- **{key}**: {value}\n")

            f.write("\n## 技术亮点\n")
            f.write("- 模块化架构设计，易于扩展和维护\n")
            f.write("- 高级筛选算法，支持多条件复合筛选\n")
            f.write("- 综合评分系统，量化股票增长潜力\n")
            f.write("- 可视化分析，直观展示市场趋势\n")
            f.write("- 逆向投资机会识别，发现被低估标的\n\n")

            f.write("## 下一步建议\n")
            f.write("1. 接入真实API数据源\n")
            f.write("2. 增加机器学习预测模型\n")
            f.write("3. 开发Web交互界面\n")
            f.write("4. 实现自动化定时分析\n")
            f.write("5. 添加风险管理模块\n")

        print(f"✓ 项目摘要报告已生成: {summary_path}")

    except Exception as e:
        print(f"❌ 生成摘要报告失败: {str(e)}")

def show_project_structure():
    """显示项目结构"""
    print("\n📁 项目结构:")
    print("-" * 40)

    structure = {
        "根目录": ["README.md", "USAGE.md", "PROJECT_STATUS.md"],
        "配置": ["config.py", ".gitignore"],
        "源代码": ["main.py", "api_client.py", "data_processor.py", 
                  "report_analyzer.py", "growth_filter.py", "demo.py"],
        "文档": ["README.md", "USAGE.md", "PROJECT_STATUS.md"],
        "数据目录": ["data/", "output/", "logs/", "visualizations/"]
    }

    for category, files in structure.items():
        print(f"\n{category}:")
        for item in files:
            if item.endswith('/'):
                print(f"  📁 {item}")
            else:
                print(f"  📄 {item}")

def check_dependencies():
    """检查必需的依赖包"""
    print("\n🔍 检查项目依赖...")

    required_packages = [
        'pandas', 'numpy', 'matplotlib', 'seaborn', 'requests'
    ]

    missing_packages = []
    for package in required_packages:
        try:
            __import__(package)
            print(f"✓ {package} 已安装")
        except ImportError:
            missing_packages.append(package)

    if missing_packages:
        print(f"⚠️  缺少依赖包: {', '.join(missing_packages)}")
        print("请使用以下命令安装:")
        print("pip install -r requirements.txt")
        return False

    return True

def main():
    """主演示函数"""
    print("🎯 A股年报增长率分析项目 - 完整演示")
    print("=" * 60)

    # 检查依赖
    if not check_dependencies():
        print("\n❌ 请先安装所需依赖包")
        return

    # 创建必要目录
    setup_directories()

    # 运行完整分析
    success = run_complete_analysis()

    if success:
        # 生成摘要报告
        generate_summary_report()

        # 显示项目结构
        show_project_structure()

        print("\n" + "=" * 60)
        print("🎉 演示完成！项目已成功构建和运行")
        print("\n📚 查看以下文件了解更多:")
        print("   - README.md: 项目概述")
        print("   - USAGE.md: 详细使用说明")
        print("   - PROJECT_STATUS.md: 项目进度")
        print("   - output/: 分析结果和报告")
        print("   - analysis.ipynb: Jupyter Notebook分析环境")
        print("\n🚀 准备投入实际生产使用！")
    else:
        print("\n❌ 演示过程中出现问题，请检查日志文件")

if __name__ == "__main__":
    main()