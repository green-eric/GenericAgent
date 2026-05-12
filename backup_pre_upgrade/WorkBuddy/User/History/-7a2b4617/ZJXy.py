#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
===============================================================================
  数据获取层 - 基于 AkShare 同花顺接口
  负责获取三大报表（利润表、资产负债表、现金流量表）及行情数据
  新API返回长格式数据，需要透视转换
===============================================================================
"""
import akshare as ak
import pandas as pd
import time
from typing import Dict, Optional
from config import DATA_CONFIG

# 字段映射表（新API返回英文metric_name）
PROFIT_COLS = {
    'operating_income': 'revenue',
    'operating_costs': 'oper_cost',
    'operating_profit': 'oper_profit',
    'parent_holder_net_profit': 'net_profit_parent',
    'index_deduct_holder_net_profit': 'net_profit_ex',
    'interest_expenses': 'fin_expense',
    'financial_interest_expenses': 'fin_expense',
}

BALANCE_COLS = {
    'assets_total': 'total_assets',
    'total_debt': 'total_liab',
    'parent_holder_equity_total': 'equity_parent',
    'holder_equity_total': 'total_equity',
    'total_current_assets': 'current_assets',
    'current_total_debt': 'current_liab',
}

CASHFLOW_COLS = {
    'act_cash_flow_net': 'ocf',
    'pay_fixed_assets_etc_cash': 'capex',
    'sale_received_cash': 'cash_from_sales',
}

# 需要的指标（减少数据量）
PROFIT_METRICS = {'operating_income', 'operating_costs', 'operating_profit', 
                  'parent_holder_net_profit', 'interest_expenses'}
BALANCE_METRICS = {'assets_total', 'total_debt', 'parent_holder_equity_total',
                   'holder_equity_total', 'total_current_assets', 'current_total_debt'}
CASHFLOW_METRICS = {'act_cash_flow_net', 'pay_fixed_assets_etc_cash', 'sale_received_cash'}

# 额外需要的同比指标（用于成长性评分）
PROFIT_YOY_METRICS = {'operating_income', 'parent_holder_net_profit'}  # 需要保留 yoy 字段

# 需要保留的最终列
FINAL_COLS = [
    'report_date', 'ann_date',
    'revenue', 'oper_cost', 'oper_profit',
    'net_profit_parent', 'fin_expense',
    'total_assets', 'total_liab', 'total_equity', 'equity_parent',
    'current_assets', 'current_liab',
    'ocf', 'capex', 'cash_from_sales',
]


def retry_fetch(func, *args, **kwargs) -> pd.DataFrame:
    """带重试的抓取"""
    max_retry = DATA_CONFIG['max_retry']
    for attempt in range(max_retry):
        try:
            df = func(*args, **kwargs)
            if df is not None and not df.empty:
                return df
        except Exception as e:
            if attempt < max_retry - 1:
                time.sleep(DATA_CONFIG['retry_delay'])
            else:
                raise
    return pd.DataFrame()


class DataProvider:
    """财务数据提供者"""

    @classmethod
    def _fetch_and_pivot(cls, symbol, api_func, api_name, needed_metrics):
        """获取数据并透视，只保留需要的指标"""
        try:
            df = api_func(symbol=symbol, indicator="按报告期")
            if df is None or df.empty:
                return None
            # 先过滤指标，大幅减少数据量
            df = df[df['metric_name'].isin(needed_metrics)]
            if df.empty:
                return None
            # 透视
            pivot = df.pivot_table(
                index='report_date',
                columns='metric_name',
                values='value',
                aggfunc='first'
            ).reset_index()
            return pivot
        except Exception as e:
            return None

    @classmethod
    def get_combined_financials(cls, symbol: str) -> pd.DataFrame:
        """
        获取个股完整财务数据，按报告期合并。
        新API返回长格式数据，先过滤再透视。
        """
        # 1) 利润表
        profit = None
        for api_name, api_func in [
            ('stock_financial_benefit_new_ths', ak.stock_financial_benefit_new_ths),
            ('stock_financial_benefit_ths', ak.stock_financial_benefit_ths),
        ]:
            profit = cls._fetch_and_pivot(symbol, api_func, api_name, PROFIT_METRICS)
            if profit is not None and not profit.empty:
                break
        if profit is None or profit.empty:
            return pd.DataFrame()

        # 2) 资产负债表
        balance = None
        for api_name, api_func in [
            ('stock_financial_debt_new_ths', ak.stock_financial_debt_new_ths),
            ('stock_financial_debt_ths', ak.stock_financial_debt_ths),
        ]:
            balance = cls._fetch_and_pivot(symbol, api_func, api_name, BALANCE_METRICS)
            if balance is not None and not balance.empty:
                break
        if balance is None or balance.empty:
            return pd.DataFrame()

        # 3) 现金流量表
        cashflow = None
        for api_name, api_func in [
            ('stock_financial_cash_new_ths', ak.stock_financial_cash_new_ths),
            ('stock_financial_cash_ths', ak.stock_financial_cash_ths),
        ]:
            cashflow = cls._fetch_and_pivot(symbol, api_func, api_name, CASHFLOW_METRICS)
            if cashflow is not None and not cashflow.empty:
                break
        if cashflow is None or cashflow.empty:
            return pd.DataFrame()

        # 4) 字段映射与合并
        profit = profit.rename(columns=PROFIT_COLS)
        balance = balance.rename(columns=BALANCE_COLS)
        cashflow = cashflow.rename(columns=CASHFLOW_COLS)

        # 去重列名
        profit = profit.loc[:, ~profit.columns.duplicated(keep='first')]
        balance = balance.loc[:, ~balance.columns.duplicated(keep='first')]
        cashflow = cashflow.loc[:, ~cashflow.columns.duplicated(keep='first')]

        # 转换日期
        profit['report_date'] = pd.to_datetime(profit['report_date'])
        balance['report_date'] = pd.to_datetime(balance['report_date'])
        cashflow['report_date'] = pd.to_datetime(cashflow['report_date'])

        # 合并
        df = pd.merge(profit, balance, on='report_date', how='inner')
        df = pd.merge(df, cashflow, on='report_date', how='inner')

        # 确保 report_date 是 datetime
        df['report_date'] = pd.to_datetime(df['report_date'])

        # 保留需要的列
        for col in FINAL_COLS:
            if col not in df.columns:
                df[col] = 0
        df = df[FINAL_COLS].sort_values('report_date')

        # 数值转 float
        for col in FINAL_COLS:
            if col not in ('report_date', 'ann_date'):
                try:
                    df[col] = df[col].astype(float)
                except:
                    df[col] = 0

        # 财务费用取绝对值
        if 'fin_expense' in df.columns:
            df['fin_expense'] = df['fin_expense'].abs()

        # 公告日估算（按报告期类型使用不同偏移，更贴近实际披露节奏）
        def estimate_ann_date(report_date):
            month = report_date.month
            if month == 12:
                # 年报：次年 3~4 月披露，取 120 天
                return report_date + pd.Timedelta(days=120)
            elif month == 3:
                # 一季报：当年 4 月披露，取 30 天
                return report_date + pd.Timedelta(days=30)
            elif month == 6:
                # 中报：当年 7~8 月披露，取 60 天
                return report_date + pd.Timedelta(days=60)
            elif month == 9:
                # 三季报：当年 10 月披露，取 30 天
                return report_date + pd.Timedelta(days=30)
            else:
                return report_date + pd.Timedelta(days=45)
        
        df['ann_date'] = df['report_date'].apply(estimate_ann_date)

        return df

    @staticmethod
    def get_stock_quote(symbol: str) -> Dict[str, float]:
        """获取实时行情（总市值、PE-TTM）"""
        total_mv = 0.0
        pe = 0.0

        try:
            info = ak.stock_individual_info_em(symbol=symbol)

            # 总市值（数值，单位：元）
            mv_rows = info[info['item'] == '总市值']
            if not mv_rows.empty:
                try:
                    total_mv = float(mv_rows['value'].values[0])
                except:
                    pass

            # 尝试多种 PE 字段名
            for pe_field in ['市盈率-动态', '市盈率', 'PE(TTM)', 'pe_ttm', '市盈率(动)']:
                pe_rows = info[info['item'] == pe_field]
                if not pe_rows.empty:
                    try:
                        val = float(pe_rows['value'].values[0])
                        if val > 0:
                            pe = val
                            break
                    except:
                        continue
        except:
            pass

        # 如果 PE 仍为 0，用总市值/净利润估算
        if pe <= 0 and total_mv > 0:
            try:
                fin = ak.stock_financial_benefit_new_ths(symbol=symbol, indicator="按报告期")
                if fin is not None and not fin.empty:
                    latest_date = fin['report_date'].max()
                    net_profit_row = fin[(fin['metric_name'] == 'parent_holder_net_profit') & 
                                         (fin['report_date'] == latest_date)]
                    if not net_profit_row.empty:
                        net_profit = float(net_profit_row['value'].values[0])
                        if net_profit > 0:
                            pe = total_mv / net_profit
            except:
                pass

        return {'total_mv': total_mv, 'pe_ttm': pe}

    @staticmethod
    def get_stock_name(symbol: str) -> str:
        """获取股票名称"""
        try:
            info = ak.stock_individual_info_em(symbol=symbol)
            name_rows = info[info['item'] == '股票简称']
            if not name_rows.empty:
                return str(name_rows['value'].values[0])
        except:
            pass
        return symbol

    @staticmethod
    def get_industry(symbol: str) -> Optional[str]:
        """获取行业分类"""
        try:
            info = ak.stock_individual_info_em(symbol=symbol)
            ind_rows = info[info['item'] == '行业']
            if not ind_rows.empty:
                return str(ind_rows['value'].values[0])
        except:
            pass
        return None

    @staticmethod
    def is_st_stock(symbol: str) -> bool:
        """判断是否 ST 股票"""
        try:
            info = ak.stock_individual_info_em(symbol=symbol)
            name_rows = info[info['item'] == '股票简称']
            if not name_rows.empty:
                name = str(name_rows['value'].values[0])
                return 'ST' in name or '*ST' in name
        except:
            pass
        return False