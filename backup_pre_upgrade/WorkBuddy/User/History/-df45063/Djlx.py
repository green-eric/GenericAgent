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
        将累计值拆分为单季值（完全向量化版，零iterrows）。

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
                     'net_profit_ex', 'ocf', 'capex', 'cash_from_sales', 'fin_expense']
        flow_cols = [c for c in flow_cols if c in df.columns]

        # 添加辅助列
        df['_year'] = df['report_date'].dt.year
        df['_month'] = df['report_date'].dt.month
        df['_qtr'] = df['_month'].map({3: 1, 6: 2, 9: 3, 12: 4})

        # 初始化单季列
        for col in flow_cols:
            df[f'q_{col}'] = np.nan

        # 按年份+季度排序确保正确
        df = df.sort_values(['_year', '_month']).reset_index(drop=True)

        # 完全向量化：按(year, qtr)排序后直接用shift获取上一季度值
        prev_qtr_map = {2: 1, 3: 2, 4: 3}
        
        for col in flow_cols:
            q_col = f'q_{col}'
            
            # Q1直接赋值
            q1_mask = df['_qtr'] == 1
            df.loc[q1_mask, q_col] = df.loc[q1_mask, col]
            
            # Q2/Q3/Q4: 当前累计值 - 同年前一季度累计值
            # 用 groupby + shift 实现：同一年内按季度排序，shift(1)取上一季
            df['_prev_val'] = df.groupby('_year')[col].shift(1)
            df['_prev_qtr'] = df.groupby('_year')['_qtr'].shift(1)
            
            for qtr, prev_qtr in prev_qtr_map.items():
                mask = (df['_qtr'] == qtr) & (df['_prev_qtr'] == prev_qtr)
                valid = mask & df[col].notna() & df['_prev_val'].notna()
                df.loc[valid, q_col] = df.loc[valid, col] - df.loc[valid, '_prev_val']
            
            df.drop(columns=['_prev_val', '_prev_qtr'], inplace=True)

        # 清理辅助列
        df = df.drop(columns=['_year', '_month', '_qtr'])
        self.df = df

        # 计算单季同比增速
        self._calc_yoy()

    def _calc_yoy(self):
        """计算单季同比增速（完全向量化版，零iterrows）"""
        df = self.df

        for col in ['net_profit_parent', 'revenue']:
            q_col = f'q_{col}'
            yoy_col = f'q_{col}_yoy'
            if q_col not in df.columns:
                continue

            df[yoy_col] = np.nan

            # 构建 report_date → q_value 的映射（仅非NaN值）
            valid_mask = df[q_col].notna()
            if valid_mask.sum() < 2:
                continue

            # 用 merge 实现同比查找：当前日期 - 1年 → 去年同期值
            df['_date_key'] = df['report_date'] - pd.DateOffset(years=1)
            
            # 创建查找表：report_date → q_value
            lookup = df.loc[valid_mask, ['report_date', q_col]].copy()
            lookup.columns = ['_date_key', '_prev_val']
            lookup = lookup.set_index('_date_key')['_prev_val']
            
            # 向量化查找
            matched = df['_date_key'].map(lookup)
            
            # 计算同比：仅当分母非零且非NaN时
            valid_base = matched.notna() & (matched != 0) & df[q_col].notna()
            df.loc[valid_base, yoy_col] = (df.loc[valid_base, q_col] / matched[valid_base] - 1) * 100
            
            df.drop(columns=['_date_key'], inplace=True)

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
        # 只要有任一净利润列可用的行就保留（兼容只有扣非或只有归母的情况）
        has_profit = self.df['q_net_profit_parent'].notna() | self.df.get('q_net_profit_ex', pd.Series([False]*len(self.df))).notna()
        df = self.df[has_profit].sort_values('report_date').tail(8)

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
                 'net_profit_ratio', 'cash_recovery_rate', 'de_ratio', 'current_ratio',
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

    def get_completeness_info(self) -> Dict:
        """
        计算数据完整度详情。
        
        评估维度：
        1. 季度覆盖率：最近4个季度是否全部存在（TTM计算的核心依赖）
        2. 关键字段缺失：最近4季度中核心财务字段是否全为NaN
        
        Returns:
            dict:
            - score: float (0-100) 综合完整度评分（季度覆盖60% + 字段质量40%）
            - quarter_coverage: str 如 "4/4" 或 "3/4 缺24Q2,24Q3"
            - field_gaps: str 如 "无" 或 "营收,归母净利,OCF"
        """
        df = self.df

        if df is None or df.empty:
            return {
                'score': 0,
                'quarter_coverage': '0/4',
                'field_gaps': '全部缺失'
            }

        # 确保 report_date 是 datetime
        if not pd.api.types.is_datetime64_any_dtype(df['report_date']):
            df = df.copy()
            df['report_date'] = pd.to_datetime(df['report_date'], errors='coerce')

        df_sorted = df.sort_values('report_date').reset_index(drop=True)

        # ---- 1. 季度覆盖率 ----
        # 以最新报告期为基准，回推4个季度，检查是否存在
        latest_date = df_sorted['report_date'].max()
        latest_year = latest_date.year
        latest_month = latest_date.month
        latest_qtr = {3: 1, 6: 2, 9: 3, 12: 4}.get(latest_month, 0)

        if latest_qtr == 0:
            return {
                'score': 0,
                'quarter_coverage': '0/4',
                'field_gaps': '报告期异常'
            }

        # 生成期望的最近4个季度（倒推）
        expected = []
        y, q = latest_year, latest_qtr
        for _ in range(4):
            expected.append((y, q))
            q -= 1
            if q <= 0:
                q = 4
                y -= 1
        expected.reverse()  # 按时间正序

        # 实际存在的季度集合
        actual = set()
        for rd in df_sorted['report_date']:
            if pd.notna(rd):
                m = rd.month
                qtr = {3: 1, 6: 2, 9: 3, 12: 4}.get(m, 0)
                if qtr > 0:
                    actual.add((rd.year, qtr))

        # 逐个检查
        covered_count = sum(1 for yq in expected if yq in actual)
        missing = [(y, q) for y, q in expected if (y, q) not in actual]

        coverage_str = f"{covered_count}/4"
        if missing:
            miss_labels = [f"{y}Q{q}" for y, q in missing]
            coverage_str += f" 缺{','.join(miss_labels)}"

        # ---- 2. 关键字段缺失检查（最近4季度） ----
        recent = df_sorted.tail(4)

        # 核心字段：流量项（利润表+现金流量表） + 存量项（资产负债表）
        key_fields = {
            'revenue': '营收',
            'net_profit_parent': '归母净利',
            'ocf': 'OCF',
            'total_assets': '总资产',
            'equity_parent': '归母权益',
            'total_equity': '股东权益',
        }

        gaps = []
        for field, label in key_fields.items():
            if field not in recent.columns:
                gaps.append(label)
            else:
                # 判定标准：最近4季度全部为NaN才算缺失
                # 0是合法值（银行股某些字段为0），不算缺失
                if recent[field].isna().all():
                    gaps.append(label)

        gaps_str = '无' if not gaps else ','.join(gaps)

        # ---- 3. 综合评分 ----
        quarter_score = covered_count / 4 * 100
        field_score = (1 - len(gaps) / len(key_fields)) * 100
        overall = quarter_score * 0.6 + field_score * 0.4

        return {
            'score': round(overall, 0),
            'quarter_coverage': coverage_str,
            'field_gaps': gaps_str,
        }

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