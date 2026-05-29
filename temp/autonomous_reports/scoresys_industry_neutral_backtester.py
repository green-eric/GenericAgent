#!/usr/bin/env python3
"""
ScoreSys行业中性化回测框架
基于现有322万行数据实现行业中性化打分，验证IC提升效果
"""

import sqlite3
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import json
import sys
import os
sys.path.append(r'D:\\Project\\ScoreSys')

from industry_neutral_backtest import main as original_main

class IndustryNeutralBacktester:
    def __init__(self, db_path, config_path=None):
        self.db_path = db_path
        self.config_path = config_path or r'D:\\Project\\ScoreSys\\config.yaml'
        self.industry_map = {}
        self.load_industry_mapping()
        
    def load_industry_mapping(self):
        """加载行业映射"""
        map_file = r'D:\\Project\\ScoreSys\\industry_map_akshare.json'
        if os.path.exists(map_file):
            with open(map_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.industry_map = data.get('data', {})
                
    def get_industry_data(self, start_date=None, end_date=None):
        """获取行业数据"""
        conn = sqlite3.connect(self.db_path)
        
        query = """
        SELECT 
            q.symbol,
            q.trade_date,
            q.close,
            s.industry_code,
            s.industry_name
        FROM quotes q
        LEFT JOIN stocks s ON q.symbol = s.symbol
        WHERE q.trade_date >= ?
        ORDER BY q.trade_date, q.symbol
        """
        
        params = [start_date or '2020-01-01']
        if end_date:
            query += " AND q.trade_date <= ?"
            params.append(end_date)
            
        df = pd.read_sql_query(query, conn, params=params)
        conn.close()
        
        return df
        
    def calculate_industry_neutral_factor(self, df, factor_func, lookback_days=60):
        """计算行业中性化因子"""
        # 按日期和行业分组计算因子
        df['date'] = pd.to_datetime(df['trade_date'])
        
        # 应用因子函数
        df['factor_raw'] = df.groupby(['symbol', 'date'], group_keys=False).apply(
            lambda x: factor_func(x)
        )
        
        # 行业中性化处理
        df['factor_neutral'] = self._industry_neutralize(
            df['factor_raw'], df['industry_name']
        )
        
        return df
        
    def _industry_neutralize(self, factor_values, industry_names):
        """行业中性化核心算法"""
        df_temp = pd.DataFrame({
            'factor': factor_values,
            'industry': industry_names
        })
        
        # 行业内排序标准化
        df_temp['rank'] = df_temp.groupby('industry')['factor'].rank(method='first')
        min_rank = df_temp['rank'].min()
        max_rank = df_temp['rank'].max()
        
        if max_rank > min_rank:
            df_temp['neutralized'] = (df_temp['rank'] - min_rank) / (max_rank - min_rank)
        else:
            df_temp['neutralized'] = 0.5
            
        return df_temp['neutralized'].values
        
    def run_backtest(self, start_date='2020-01-01', end_date='2026-12-31'):
        """运行完整回测"""
        print(f"🚀 开始行业中性化回测: {start_date} 至 {end_date}")
        
        # 获取数据
        data = self.get_industry_data(start_date, end_date)
        print(f"📊 获取到 {len(data):,} 条记录")
        
        # 计算原始因子
        data = self.calculate_industry_neutral_factor(data, self._simple_factor)
        
        # 计算IC对比
        results = self.calculate_ic_comparison(data)
        
        # 保存结果
        self.save_results(results, start_date, end_date)
        
        return results
        
    def _simple_factor(self, group):
        """简单因子示例"""
        return group['close'].rolling(window=20).mean()
        
    def calculate_ic_comparison(self, data):
        """计算IC对比"""
        results = {
            'original_ic': [],
            'neutralized_ic': [],
            'dates': [],
            'improvement': []
        }
        
        # 按时间窗口计算IC
        dates = sorted(data['date'].unique())
        
        for date in dates[-100:]:  # 最近100个交易日
            window_data = data[data['date'] <= date].copy()
            
            # 计算原始因子IC
            original_ic, _ = self._calculate_window_ic(window_data, False)
            
            # 计算中性化因子IC  
            neutralized_ic, _ = self._calculate_window_ic(window_data, True)
            
            results['original_ic'].append(original_ic)
            results['neutralized_ic'].append(neutralized_ic)
            results['dates'].append(date.strftime('%Y-%m-%d'))
            results['improvement'].append(neutralized_ic - original_ic)
            
        return results
        
    def _calculate_window_ic(self, data, use_neutral):
        """计算窗口期IC"""
        # 简化的IC计算逻辑
        if len(data) < 10:
            return 0, 1
            
        # 这里应该实现完整的IC计算
        # 使用Spearman相关系数
        return 0.05, 0.01  # 示例值
        
    def save_results(self, results, start_date, end_date):
        """保存回测结果"""
        output = {
            'metadata': {
                'start_date': start_date,
                'end_date': end_date,
                'timestamp': datetime.now().isoformat(),
                'data_points': len(results['dates']),
                'avg_original_ic': sum(results['original_ic']) / len(results['original_ic']),
                'avg_neutralized_ic': sum(results['neutralized_ic']) / len(results['neutralized_ic']),
                'ic_improvement': sum(results['improvement']) / len(results['improvement'])
            },
            'results': results
        }
        
        os.makedirs(output_dir, exist_ok=True)
        output_file = os.path.join(output_dir, f'scoresys_industry_neutral_bt_{datetime.now().strftime("%Y%m%d")}.json')
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(output, f, indent=2, ensure_ascii=False)
            
        print(f"💾 结果已保存: {output_file}")
        
        return output_file

if __name__ == "__main__":
    backtester = IndustryNeutralBacktester(
        db_path=r'D:\\Project\\ScoreSys\\stock_data.db'
    )
    
    results = backtester.run_backtest(
        start_date='2020-01-01',
        end_date='2026-12-31'
    )
