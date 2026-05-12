#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================================
 指标计算引擎 - 单季拆分 + TTM + 杠杆
================================================================================
"""
import pandas as pd
import numpy as np
from typing import Dict
from config import DATA_CONFIG


class IndicatorCalculator:
    """
    输入: 包含完整财务列的 DataFrame（来自 DataProvider）
    计算:
        - 单季拆分: q_net_profit, q_revenue, q_oper_profit, q_ocf, q_capex, q_cash_from_sales, q_fin_expense
        - 单季同比增速: q_net_profit_yoy, q_revenue_yoy
        - TTM 指标: roe_ttm, gross_margin_ttm, net_margin_ttm, fcf_ttm, net_profit_ratio, cash_recovery_rate
        - 杠杆指标: de_ratio, current_ratio, asset_liability_ratio, interest_cover

    关键：支持 ann_date 公告日过滤（防未来函数）
    """

    def __init__(self, df_fin: pd.DataFrame, eval_date: pd.Timestamp = None):
        self.df = df_fin.copy().reset_index(drop=True)
        self.eval_date = eval_date
        self._filter_by_ann_date()
        self._split_quarterly()
        self._calc_ttm_and_leverage()

    def _filter_by_ann_date(self):
        """
        【防未来函数核心修复】
        仅使用公告日 <= 评估日的财报数据。
        若评估日在某财报公告之前，该财报不可用。
        """
        if self.eval_date is None:
            return  # 无评估日期则跳过

        if 'ann_date' in self.df.columns:
            mask = self.df['ann_date'] <= self.eval_date
            removed = len(self.df) - mask.sum()
            if removed > 0:
                print(f"    [防未来] 因公告日过滤移除 {removed} 条记录")
            self.df = self.df[mask].copy()

    # -------------------------------------------------------------------------
    # 单季拆分
    # -------------------------------------------------------------------------
    def _split_quarterly(self):
        """
        将累计值拆分为单季值。

        规则：
        - Q1 (3月): 直接取一季报累计值
        - Q2 (6月): 中报累计值 - Q1
        - Q3 (9月): 三季报累计值 - 中报
        - Q4 (12月): 年报累计值 - 三季报
        """
        df = self.df
        # DB读取后report_date可能是字符串，确保转datetime
        if not pd.api.types.is_datetime64_any_dtype(df['report_date']):
            df['report_date'] = pd.to_datetime(df['report_date'], errors='coerce')
        if 'ann_date' in df.columns and not pd.api.types.is_datetime64_any_dtype(df['ann_date']):
            df['ann_date'] = pd.to_datetime(df['ann_date'], errors='coerce')

        # 需要拆分的列（流量项目）
        flow_cols = ['revenue', 'oper_cost', 'oper_profit', 'net_profit_parent',
                     'net_profit_ex', 'ocf', 'capex', 'cash_from_sales', 'fin_expense']        # 确保列存在
        flow_cols = [c for c in flow_cols if c in df.columns]

        # 初始化单季列
        for col in flow_cols:
            df[f'q_{col}'] = np.nan

        # 按月份分组处理
        # 报告期月份映射
        month_map = {3: 'Q1', 6: 'Q2', 9: 'Q3', 12: 'Q4'}

        for year in df['report_date'].dt.year.unique():
            year_data = df[df['report_date'].dt.year == year].copy()

            for idx, row in year_data.iterrows():
                month = row['report_date'].month
                quarter = month_map.get(month)

                if quarter is None:
                    continue

                i = idx

                if quarter == 'Q1':
                    # Q1 直接取累计值
                    for col in flow_cols:
                        val = row[col]
                        # 兼容 pandas 3.x：确保取标量
                        if isinstance(val, pd.Series):
                            val = val.iloc[0] if len(val) > 0 else np.nan
                        if pd.notna(val):
                            df.at[i, f'q_{col}'] = val
                else:
                    # Q2/Q3/Q4: 累计值 - 上期累计值
                    prev_month_map = {6: 3, 9: 6, 12: 9}
                    prev_month = prev_month_map[month]

                    prev_data = year_data[year_data['report_date'].dt.month == prev_month]
                    if not prev_data.empty:
                        prev_row = prev_data.iloc[0]
                        for col in flow_cols:
                            curr_val = row[col]
                            prev_val = prev_row[col]
                            # 兼容 pandas 3.x：确保取标量
                            if isinstance(curr_val, pd.Series):
                                curr_val = curr_val.iloc[0] if len(curr_val) > 0 else np.nan
                            if isinstance(prev_val, pd.Series):
                                prev_val = prev_val.iloc[0] if len(prev_val) > 0 else np.nan
                            if pd.notna(curr_val) and pd.notna(prev_val):
                                df.at[i, f'q_{col}'] = curr_val - prev_val
                            else:
                                df.at[i, f'q_{col}'] = np.nan
                    else:
                        for col in flow_cols:
                            df.at[i, f'q_{col}'] = np.nan

        self.df = df

        # 计算单季同比增速
        self._calc_yoy()

    def _calc_yoy(self):
        """计算单季同比增速"""
        df = self.df

        for col in ['net_profit_parent', 'revenue']:
            yoy_col = f'q_{col}_yoy'
            df[yoy_col] = np.nan

            for i, row in df.iterrows():
                if pd.isna(row[f'q_{col}']):
                    continue

                target_date = row['report_date']
                last_year_date = target_date - pd.DateOffset(years=1)

                prev_rows = df[df['report_date'] <= last_year_date].tail(1)
                if not prev_rows.empty:
                    base_val = prev_rows.iloc[0][f'q_{col}']
                    if base_val and base_val != 0 and not np.isnan(base_val):
                        df.at[i, yoy_col] = (row[f'q_{col}'] / base_val - 1) * 100

        self.df = df

    # -------------------------------------------------------------------------
    # TTM + 杠杆计算
    # -------------------------------------------------------------------------
    def _calc_ttm_and_leverage(self):
        """
        基于最近 4 个季度的单季数据计算 TTM 指标和杠杆指标。

        TTM 规则：
        - 流量项目（利润表/现金流量表）：最近 4 个单季求和
        - 存量项目（资产负债表）：直接取最新报告期的期末值

        扣非净利润优先：若 net_profit_ex 存在则使用，否则用 net_profit_parent
        """
        df = self.df.dropna(subset=['q_net_profit_parent']).sort_values('report_date').tail(8)

        if len(df) < DATA_CONFIG['min_quarters']:
            print(f"  警告：可用季度数据不足（{len(df)} < {DATA_CONFIG['min_quarters']}）")
            self._init_empty()
            return

        # 最近 4 个季度
        recent4 = df.tail(4)

        # TTM 流量数据 - 扣非净利润优先（需有非零值才算有效）
        if 'q_net_profit_ex' in df.columns and (df['q_net_profit_ex'] != 0).any():
            ttm_net_profit = recent4['q_net_profit_ex'].sum()
            self._use_ex_profit = True
        else:
            ttm_net_profit = recent4['q_net_profit_parent'].sum()
            self._use_ex_profit = False

        self._ttm_net_profit = ttm_net_profit
        self._ttm_revenue = recent4['q_revenue'].sum()
        self._ttm_ocf = recent4['q_ocf'].sum()
        self._ttm_capex = recent4['q_capex'].sum() if 'q_capex' in recent4.columns else 0
        self._ttm_cash_sales = recent4['q_cash_from_sales'].sum() if 'q_cash_from_sales' in recent4.columns else 0
        self._ttm_oper_cost = recent4['q_oper_cost'].sum() if 'q_oper_cost' in recent4.columns else 0
        self._ttm_fin_expense = recent4['q_fin_expense'].sum() if 'q_fin_expense' in recent4.columns else 0
        self._ttm_oper_profit = recent4['q_oper_profit'].sum() if 'q_oper_profit' in recent4.columns else 0

        # 最新资产负债表（存量）
        latest = df.iloc[-1]
        self._equity_parent = latest.get('equity_parent', 0) or 0
        self._total_assets = latest.get('total_assets', 0) or 0
        self._total_liab = latest.get('total_liab', 0) or 0
        self._total_equity = latest.get('total_equity', 0) or 0
        self._current_assets = latest.get('current_assets', 0) or 0
        self._current_liab = latest.get('current_liab', 0) or 0

        # 最新单季同比（用于成长性评分）
        # 从 self.df 中取最新一期的同比数据（_split_quarterly 已计算）
        latest_row = self.df.iloc[-1]
        self.q_net_profit_yoy = latest_row.get('q_net_profit_parent_yoy', 0) or 0
        self.q_revenue_yoy = latest_row.get('q_revenue_yoy', 0) or 0
        
        # 如果同比为0（数据不足），尝试用最近4季度近似
        if self.q_net_profit_yoy == 0 or self.q_revenue_yoy == 0:
            try:
                # 取最近4季度和去年同期的数据
                recent = self.df.dropna(subset=['q_net_profit_parent']).tail(4)
                prev = self.df.dropna(subset=['q_net_profit_parent']).tail(8).head(4)
                if len(recent) >= 4 and len(prev) >= 4:
                    curr_rev = recent['q_revenue'].sum()
                    prev_rev = prev['q_revenue'].sum()
                    curr_profit = recent['q_net_profit_parent'].sum()
                    prev_profit = prev['q_net_profit_parent'].sum()
                    if prev_rev > 0:
                        self.q_revenue_yoy = (curr_rev / prev_rev - 1) * 100
                    if prev_profit > 0:
                        self.q_net_profit_yoy = (curr_profit / prev_profit - 1) * 100
            except:
                pass

        self._calc_profitability()
        self._calc_cashflow()
        self._calc_leverage()

        self.report_date = df.iloc[-1]['report_date']

    def _calc_profitability(self):
        """盈利能力指标"""
        # ROE = TTM 归母净利润 / 归母权益 × 100%
        self.roe_ttm = (self._ttm_net_profit / self._equity_parent * 100) if self._equity_parent else 0
        # 毛利率 = (TTM营收 - TTM成本) / TTM营收 × 100%
        # 注意：金融行业（银行/保险）oper_cost=0，毛利率不适用，应返回0
        if self._ttm_revenue and self._ttm_oper_cost > 0:
            self.gross_margin_ttm = ((self._ttm_revenue - self._ttm_oper_cost) / self._ttm_revenue * 100)
        else:
            self.gross_margin_ttm = 0
        # 净利率 = TTM归母净利润 / TTM营收 × 100%
        self.net_margin_ttm = (self._ttm_net_profit / self._ttm_revenue * 100) if self._ttm_revenue else 0

    def _calc_cashflow(self):
        """现金流质量指标"""
        # 经营现金流净额
        self.ocf_ttm = self._ttm_ocf
        # 自由现金流 = TTM经营现金流 - TTM资本支出
        self.fcf_ttm = self._ttm_ocf - self._ttm_capex
        # 净现比 = TTM经营现金流 / TTM归母净利润
        self.net_profit_ratio = (self._ttm_ocf / self._ttm_net_profit) if self._ttm_net_profit else 0
        # 销售收现比 = TTM销售收现 / TTM营收
        self.cash_recovery_rate = (self._ttm_cash_sales / self._ttm_revenue) if self._ttm_revenue else 0

    def _calc_leverage(self):
        """杠杆/偿债能力指标"""
        # D/E = 总负债 / 股东权益
        self.de_ratio = (self._total_liab / self._total_equity) if self._total_equity else 0
        # 流动比率 = 流动资产 / 流动负债
        self.current_ratio = (self._current_assets / self._current_liab) if self._current_liab else 0
        # 资产负债率 = 总负债 / 总资产 × 100%
        self.asset_liability_ratio = (self._total_liab / self._total_assets * 100) if self._total_assets else 0
        # 利息覆盖倍数 = (TTM营业利润 + TTM财务费用) / TTM财务费用
        fin_exp = self._ttm_fin_expense
        self.interest_cover = ((self._ttm_oper_profit + fin_exp) / fin_exp) if fin_exp else 0

    def _init_empty(self):
        """初始化空指标"""
        attrs = ['roe_ttm', 'gross_margin_ttm', 'net_margin_ttm', 'ocf_ttm', 'fcf_ttm',
                 'net_profit_ratio', 'de_ratio', 'current_ratio',
                 'asset_liability_ratio', 'interest_cover', 'q_net_profit_yoy', 'q_revenue_yoy']
        for attr in attrs:
            setattr(self, attr, 0)
        self.report_date = None

    @property
    def net_profit_ttm(self) -> float:
        """TTM 归母净利润"""
        return self._ttm_net_profit
    
    @property
    def ocf_ttm_value(self) -> float:
        """TTM 经营现金流净额"""
        return self._ttm_ocf
    
    # fcf_yield 不在此处计算，因为需要 total_mv（市值数据）
    # 统一在 scorer.py 中计算：fcf_ttm / total_mv
    # 如需在其他地方使用，请直接计算 fcf_ttm / total_mv
    
    # cash_recovery_rate 是普通属性，在 _calc_cashflow 中计算
    # 不要在 _init_empty 中初始化它

    # -------------------------------------------------------------------------
    # 属性访问
    # -------------------------------------------------------------------------
    def get_metrics(self) -> Dict[str, float]:
        """获取所有指标（用于评分器）"""
        return {
            'roe_ttm': self.roe_ttm,
            'gross_margin_ttm': self.gross_margin_ttm,
            'net_margin_ttm': self.net_margin_ttm,
            'ocf_ttm': self.ocf_ttm,
            'fcf_ttm': self.fcf_ttm,
            'net_profit_ratio': self.net_profit_ratio,
            'cash_recovery_rate': self.cash_recovery_rate,
            'de_ratio': self.de_ratio,
            'current_ratio': self.current_ratio,
            'asset_liability_ratio': self.asset_liability_ratio,
            'interest_cover': self.interest_cover,
            'q_net_profit_yoy': self.q_net_profit_yoy,
            'q_revenue_yoy': self.q_revenue_yoy,
            'report_date': self.report_date,
        }