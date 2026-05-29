# test_industry_neutral.py
"""测试行业中性化回测框架"""

import sys
sys.path.append('.')
from scoresys_industry_neutral_backtester import IndustryNeutralBacktester

def test_basic_functionality():
    """基本功能测试"""
    print("🧪 开始基本功能测试...")
    
    backtester = IndustryNeutralBacktester(
        db_path=r'D:\\Project\\ScoreSys\\stock_data.db'
    )
    
    # 测试数据加载
    try:
        data = backtester.get_industry_data('2020-01-01', '2021-12-31')
        print(f"✅ 数据加载成功: {len(data)} 条记录")
    except Exception as e:
        print(f"❌ 数据加载失败: {e}")
        return False
        
    # 测试行业映射
    if backtester.industry_map:
        print(f"✅ 行业映射加载成功: {len(backtester.industry_map)} 个行业")
    else:
        print("❌ 行业映射加载失败")
        return False
        
    # 测试回测执行
    try:
        results = backtester.run_backtest('2020-01-01', '2021-12-31')
        print(f"✅ 回测执行成功")
        return True
    except Exception as e:
        print(f"❌ 回测执行失败: {e}")
        return False

if __name__ == "__main__":
    success = test_basic_functionality()
    if success:
        print("🎉 所有测试通过!")
    else:
        print("⚠️  测试失败，请检查错误信息")
