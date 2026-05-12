#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
===============================================================================
  数据获取层 - 基于 AkShare 同花顺接口
  负责获取三大报表（利润表、资产负债表、现金流量表）及行情数据
  新API返回长格式数据，需要透视转换
  备用数据源：westock-data / NeoData（当东方财富接口不可用时）
  
  性能优化：
  - 合并API调用：名称+行业+行情只需1次 stock_individual_info_em
  - 模块级缓存：stock_zh_a_spot_em 全市场行情只拉1次
  - westock-data profile 结果缓存
  - subprocess 统一 errors='replace' 防编码崩溃
===============================================================================
"""
import akshare as ak
import pandas as pd
import time
import subprocess
import re
import os
from typing import Dict, Optional
from config import DATA_CONFIG


# ============================================================================
# 模块级缓存（全市场行情只拉1次，避免每只股票重复5000+行请求）
# ============================================================================
_spot_cache = None
_spot_cache_time = 0
_spot_cache_ttl = 300  # 5分钟过期

_info_cache: Dict[str, Dict] = {}  # {symbol: {name, industry, total_mv, pe_ttm}}
_westock_cache: Dict[str, Optional[Dict]] = {}  # {symbol: {name, industry}}


def _get_spot_df() -> Optional[pd.DataFrame]:
    """获取全市场行情（带5分钟缓存）"""
    global _spot_cache, _spot_cache_time
    now = time.time()
    if _spot_cache is not None and (now - _spot_cache_time) < _spot_cache_ttl:
        return _spot_cache
    try:
        _spot_cache = ak.stock_zh_a_spot_em()
        _spot_cache_time = now
        return _spot_cache
    except Exception:
        return _spot_cache  # 返回旧缓存或None


def _fetch_stock_info(symbol: str) -> Dict:
    """
    一次性获取股票名称、行业、总市值、PE-TTM
    合并原来3次独立调用为1次，性能提升3倍
    """
    if symbol in _info_cache:
        return _info_cache[symbol]

    result = {
        'name': symbol,
        'industry': None,
        'total_mv': 0.0,
        'pe_ttm': 0.0,
    }

    # 主源：东方财富个股信息（1次调用获取名称+行业+市值+PE）
    try:
        info = ak.stock_individual_info_em(symbol=symbol)
        # 名称
        name_rows = info[info['item'] == '股票简称']
        if not name_rows.empty:
            val = str(name_rows['value'].values[0]).strip()
            if val and val != 'None':
                result['name'] = val
        # 行业
        for ind_col in ['行业', '所属行业', '申万行业']:
            ind_rows = info[info['item'] == ind_col]
            if not ind_rows.empty:
                val = str(ind_rows['value'].values[0]).strip()
                if val and val != 'None':
                    result['industry'] = val
                    break
        # 总市值
        mv_rows = info[info['item'] == '总市值']
        if not mv_rows.empty:
            try:
                result['total_mv'] = float(mv_rows['value'].values[0])
            except (ValueError, TypeError):
                pass
        # PE
        for pe_field in ['市盈率-动态', '市盈率', 'PE(TTM)', 'pe_ttm', '市盈率(动)']:
            pe_rows = info[info['item'] == pe_field]
            if not pe_rows.empty:
                try:
                    val = float(pe_rows['value'].values[0])
                    if val > 0:
                        result['pe_ttm'] = val
                        break
                except (ValueError, TypeError):
                    continue
    except Exception:
        pass

    _info_cache[symbol] = result
    return result


def _neodata_query(symbol: str) -> Optional[Dict]:
    """
    通过 NeoData 查询股票总市值和PE-TTM
    返回: {'total_mv': float(元), 'pe_ttm': float} 或 None
    """
    import json as _json
    try:
        script = os.path.join(
            os.path.expanduser('~'),
            '.workbuddy', 'plugins', 'marketplaces', 'cb_teams_marketplace',
            'plugins', 'finance-data', 'skills', 'neodata-financial-search',
            'scripts', 'query.py'
        )
        if not os.path.exists(script):
            return None
        r = subprocess.run(
            [os.sys.executable, script, '--query', f'{symbol} 总市值 市盈率PE'],
            capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=20
        )
        if r.returncode != 0 or not r.stdout.strip():
            return None
        data = _json.loads(r.stdout)
        if data.get('code') != '200' or not data.get('suc'):
            return None
        # 从 apiRecall 中提取行情数据
        api_data = data.get('data', {}).get('apiData', {})
        for block in api_data.get('apiRecall', []):
            content = block.get('content', '')
            if '总市值' in content or '市盈率' in content:
                nd_result = {}
                mv_match = re.search(r'总市值\(亿元\):\s*([\d,]+\.?\d*)', content)
                if mv_match:
                    nd_result['total_mv'] = float(mv_match.group(1).replace(',', '')) * 1e8
                pe_match = re.search(r'市盈率\(TTM\):\s*([\d.]+)', content)
                if not pe_match:
                    pe_match = re.search(r'市盈率.*?([\d.]+)', content)
                if pe_match:
                    nd_result['pe_ttm'] = float(pe_match.group(1))
                if nd_result:
                    return nd_result
    except Exception:
        pass
    return None


def _westock_profile(symbol: str) -> Optional[Dict]:
    """
    通过 westock-data profile 获取股票名称和行业（带缓存）
    返回: {'name': str, 'industry': str} 或 None
    """
    if symbol in _westock_cache:
        return _westock_cache[symbol]

    try:
        # 统一代码格式：600519 -> sh600519, 000858 -> sz000858
        if not (symbol.startswith('sh') or symbol.startswith('sz') or symbol.startswith('bj')):
            if symbol.startswith('6'):
                wcode = 'sh' + symbol
            elif symbol.startswith(('0', '3')):
                wcode = 'sz' + symbol
            else:
                wcode = 'bj' + symbol
        else:
            wcode = symbol

        r = subprocess.run(
            f'npx --yes westock-data-skillhub@latest profile {wcode}',
            shell=True, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=20
        )
        output = r.stdout + r.stderr
        # 解析Markdown表格（lines[0]=表头, lines[1]=分隔符, lines[2]=数据）
        lines = [l.strip() for l in output.split('\n') if l.strip().startswith('|')]
        if len(lines) >= 3:
            header = [c.strip() for c in lines[0].split('|')[1:-1]]
            values = [c.strip() for c in lines[2].split('|')[1:-1]]
            wresult = {}
            for h, v in zip(header, values):
                h_lower = h.lower()
                if 'name' in h_lower and 'code' not in h_lower:
                    wresult['name'] = v
                elif 'industry' in h_lower:
                    wresult['industry'] = v
            _westock_cache[symbol] = wresult if wresult else None
            return _westock_cache[symbol]
    except Exception:
        pass
    _westock_cache[symbol] = None
    return None


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
PROFIT_YOY_METRICS = {'operating_income', 'parent_holder_net_profit'}

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
        except Exception:
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
                except Exception:
                    df[col] = 0

        # 财务费用取绝对值
        if 'fin_expense' in df.columns:
            df['fin_expense'] = df['fin_expense'].abs()

        # 公告日估算
        def estimate_ann_date(report_date):
            month = report_date.month
            if month == 12:
                return report_date + pd.Timedelta(days=120)
            elif month == 3:
                return report_date + pd.Timedelta(days=30)
            elif month == 6:
                return report_date + pd.Timedelta(days=60)
            elif month == 9:
                return report_date + pd.Timedelta(days=30)
            else:
                return report_date + pd.Timedelta(days=45)
        
        df['ann_date'] = df['report_date'].apply(estimate_ann_date)

        return df

    @staticmethod
    def get_stock_quote(symbol: str) -> Dict[str, float]:
        """
        获取实时行情（总市值、PE-TTM）
        优化：优先从缓存 _fetch_stock_info 获取，避免重复API调用
        
        数据源降级：
        1. _fetch_stock_info（合并API调用，1次获取名称+行业+市值+PE）
        2. 全市场行情缓存 stock_zh_a_spot_em
        3. NeoData
        4. 兜底：总市值/净利润估算PE
        """
        # 先从合并缓存取
        info = _fetch_stock_info(symbol)
        total_mv = info.get('total_mv', 0)
        pe = info.get('pe_ttm', 0)

        # 备用1：全市场行情缓存（只拉1次，5分钟有效）
        if total_mv <= 0 or pe <= 0:
            try:
                spot = _get_spot_df()
                if spot is not None:
                    code_col = '代码' if '代码' in spot.columns else spot.columns[0]
                    row = spot[spot[code_col] == symbol]
                    if not row.empty:
                        if total_mv <= 0:
                            for mv_col in ['总市值', '总市值(元)']:
                                if mv_col in row.columns:
                                    try:
                                        v = float(row[mv_col].values[0])
                                        if v > 0:
                                            total_mv = v
                                            break
                                    except (ValueError, TypeError):
                                        pass
                        if pe <= 0:
                            for pe_col in ['市盈率-动态', '市盈率', 'pe_ttm']:
                                if pe_col in row.columns:
                                    try:
                                        v = float(row[pe_col].values[0])
                                        if v > 0:
                                            pe = v
                                            break
                                    except (ValueError, TypeError):
                                        pass
            except Exception:
                pass

        # 备用2：NeoData
        if total_mv <= 0 or pe <= 0:
            try:
                nd = _neodata_query(symbol)
                if nd:
                    if total_mv <= 0 and nd.get('total_mv', 0) > 0:
                        total_mv = nd['total_mv']
                    if pe <= 0 and nd.get('pe_ttm', 0) > 0:
                        pe = nd['pe_ttm']
            except Exception:
                pass

        # 最后兜底：用总市值/净利润估算PE
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
            except Exception:
                pass

        # 写回缓存
        info['total_mv'] = total_mv
        info['pe_ttm'] = pe

        return {'total_mv': total_mv, 'pe_ttm': pe}

    @staticmethod
    def get_stock_name(symbol: str) -> str:
        """
        获取股票名称（优先从合并缓存取）
        """
        info = _fetch_stock_info(symbol)
        name = info.get('name', symbol)
        if name and name != symbol:
            return name
        # 备用：westock-data
        try:
            wp = _westock_profile(symbol)
            if wp and wp.get('name'):
                info['name'] = wp['name']
                return wp['name']
        except Exception:
            pass
        return symbol

    @staticmethod
    def get_industry(symbol: str) -> Optional[str]:
        """
        获取行业分类（优先从合并缓存取）
        """
        info = _fetch_stock_info(symbol)
        industry = info.get('industry')
        if industry:
            return industry
        # 备用：westock-data
        try:
            wp = _westock_profile(symbol)
            if wp and wp.get('industry'):
                info['industry'] = wp['industry']
                return wp['industry']
        except Exception:
            pass
        return None

    @staticmethod
    def is_st_stock(symbol: str) -> bool:
        """判断是否 ST 股票"""
        name = DataProvider.get_stock_name(symbol)
        return 'ST' in name or '*ST' in name
