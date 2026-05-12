#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
===============================================================================
  数据获取层 - 基于 AkShare 同花顺接口
  性能优化 + 详细日志 + 错误可追踪
  
  优化点（V3.1 - 4000+股票优化版）：
  - 启动时预加载全市场行情缓存（一次拉取5000+行，后续全查缓存）
  - 合并API调用：名称+行业+行情只需1次 stock_individual_info_em
  - NeoData 仅做最终兜底（从主流程中移除，避免每只4s子进程开销）
  - westock-data profile 结果缓存
  - subprocess 统一 errors='replace' 防编码崩溃
  - 所有API调用带耗时日志，所有异常带原因输出
===============================================================================
"""
import akshare as ak
import pandas as pd
import time
import subprocess
import re
import os
import logging
from typing import Dict, Optional
from config import DATA_CONFIG

logger = logging.getLogger('ScoreSys')
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%H:%M:%S'
)


# ============================================================================
# 模块级缓存
# ============================================================================
_spot_cache = None
_spot_cache_time = 0
_spot_cache_ttl = 600  # 10分钟过期（4000+股票跑很久）

_info_cache: Dict[str, Dict] = {}
_westock_cache: Dict[str, Optional[Dict]] = {}
_neodata_cache: Dict[str, Optional[Dict]] = {}


def _get_spot_df() -> Optional[pd.DataFrame]:
    """获取全市场行情（带缓存）"""
    global _spot_cache, _spot_cache_time
    now = time.time()
    if _spot_cache is not None and (now - _spot_cache_time) < _spot_cache_ttl:
        return _spot_cache
    t0 = time.time()
    try:
        _spot_cache = ak.stock_zh_a_spot_em()
        _spot_cache_time = now
        elapsed = time.time() - t0
        logger.info(f"全市场行情：拉取完成，{len(_spot_cache)}行，耗时{elapsed:.1f}s")
        return _spot_cache
    except Exception as e:
        elapsed = time.time() - t0
        logger.warning(f"全市场行情：拉取失败 [{type(e).__name__}: {e}]，耗时{elapsed:.1f}s")
        return _spot_cache


def preload_market_data():
    """启动时预加载全市场行情，后续从缓存查市值/PE"""
    t0 = time.time()
    spot = _get_spot_df()
    elapsed = time.time() - t0
    if spot is not None:
        logger.info(f"预加载完成：{len(spot)}只股票 | {elapsed:.1f}s")
    else:
        logger.warning(f"预加载失败，将逐只获取 | {elapsed:.1f}s")
    return spot is not None


def _lookup_spot_cache(symbol: str) -> Dict:
    """从全市场行情缓存中查市值和PE"""
    result = {'total_mv': 0.0, 'pe_ttm': 0.0}
    spot = _get_spot_df()
    if spot is None:
        return result
    code_col = '代码' if '代码' in spot.columns else spot.columns[0]
    row = spot[spot[code_col] == symbol]
    if row.empty:
        return result
    # 市值
    for mv_col in ['总市值', '总市值(元)']:
        if mv_col in row.columns:
            try:
                v = float(row[mv_col].values[0])
                if v > 0:
                    result['total_mv'] = v
                    break
            except (ValueError, TypeError):
                pass
    # PE
    for pe_col in ['市盈率-动态', '市盈率', 'pe_ttm']:
        if pe_col in row.columns:
            try:
                v = float(row[pe_col].values[0])
                if v > 0:
                    result['pe_ttm'] = v
                    break
            except (ValueError, TypeError):
                pass
    # 名称
    name_col = '名称' if '名称' in row.columns else None
    if name_col and not row[name_col].empty:
        name_val = str(row[name_col].values[0]).strip()
        if name_val and name_val != 'nan':
            result['name'] = name_val
    return result


def _fetch_stock_info(symbol: str) -> Dict:
    """
    一次性获取股票名称、行业、总市值、PE-TTM
    优先级：缓存 → 全市场行情缓存 → 东方财富个股 → NeoData兜底
    """
    if symbol in _info_cache:
        return _info_cache[symbol]

    result = {
        'name': symbol,
        'industry': None,
        'total_mv': 0.0,
        'pe_ttm': 0.0,
    }

    # 优先：全市场行情缓存（一次拉取5000+行，后续O(1)查询）
    spot_data = _lookup_spot_cache(symbol)
    if spot_data.get('name'):
        result['name'] = spot_data['name']
    if spot_data.get('total_mv', 0) > 0:
        result['total_mv'] = spot_data['total_mv']
    if spot_data.get('pe_ttm', 0) > 0:
        result['pe_ttm'] = spot_data['pe_ttm']

    # 补充：东方财富个股信息（获取行业）
    if not result['industry']:
        t0 = time.time()
        try:
            info = ak.stock_individual_info_em(symbol=symbol)
            elapsed = time.time() - t0
            # 名称（补充）
            if result['name'] == symbol:
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
            # 补充市值/PE（如果缓存没拿到）
            if result['total_mv'] <= 0:
                mv_rows = info[info['item'] == '总市值']
                if not mv_rows.empty:
                    try:
                        result['total_mv'] = float(mv_rows['value'].values[0])
                    except (ValueError, TypeError):
                        pass
            if result['pe_ttm'] <= 0:
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
            logger.info(f"{symbol} 东方财富：{result['name']} | {result['industry']} | MV={result['total_mv']:.0f} | PE={result['pe_ttm']:.1f} | {elapsed:.1f}s")
        except Exception as e:
            elapsed = time.time() - t0
            logger.warning(f"{symbol} 东方财富：失败 [{type(e).__name__}] | {elapsed:.1f}s")

    # 最终兜底：NeoData（仅在缺关键数据时才调，有缓存避免重复）
    if result['total_mv'] <= 0 or result['pe_ttm'] <= 0 or result['industry'] is None:
        if symbol not in _neodata_cache:
            _neodata_cache[symbol] = _neodata_query(symbol)
        nd = _neodata_cache[symbol]
        if nd:
            if (not result['name'] or result['name'] == symbol) and nd.get('name'):
                result['name'] = nd['name']
            if not result['industry'] and nd.get('industry'):
                result['industry'] = nd['industry']
            if result['total_mv'] <= 0 and nd.get('total_mv', 0) > 0:
                result['total_mv'] = nd['total_mv']
            if result['pe_ttm'] <= 0 and nd.get('pe_ttm', 0) > 0:
                result['pe_ttm'] = nd['pe_ttm']

    _info_cache[symbol] = result
    return result


def _neodata_query(symbol: str) -> Optional[Dict]:
    """
    通过 NeoData 查询股票信息（名称、行业、总市值、PE-TTM）
    仅在东方财富+全市场缓存都失败时才调用
    """
    import json as _json
    t0 = time.time()
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
            [os.sys.executable, script, '--query', symbol, '--data-type', 'api'],
            capture_output=True, timeout=25,
            env={**os.environ, 'PYTHONIOENCODING': 'utf-8'}
        )
        elapsed = time.time() - t0
        if r.returncode != 0:
            return None
        stdout_text = r.stdout.decode('utf-8', errors='replace') if r.stdout else ''
        if not stdout_text.strip():
            return None
        data = _json.loads(stdout_text)
        if data.get('code') != '200' or not data.get('suc'):
            return None

        nd_result = {}
        api_data = data.get('data', {}).get('apiData', {})
        for block in api_data.get('apiRecall', []):
            content = block.get('content', '')
            if '总市值' in content or '市盈率' in content:
                mv_match = re.search(r'总市值\(亿元\)\s*[:：]\s*([\d,]+\.?\d*)', content)
                if mv_match:
                    nd_result['total_mv'] = float(mv_match.group(1).replace(',', '')) * 1e8
                pe_match = re.search(r'市盈率\(TTM\)\s*[:：]\s*([\d.]+)', content)
                if pe_match:
                    nd_result['pe_ttm'] = float(pe_match.group(1))
            if '所属一级行业' in content:
                ind_match = re.search(r'所属一级行业[：:]\s*([^，,。\n]+)', content)
                if ind_match:
                    nd_result['industry'] = ind_match.group(1).strip()
        for entity in api_data.get('entity', []):
            name_val = entity.get('code', '')
            if name_val:
                nd_result['name'] = name_val

        if nd_result:
            logger.info(f"{symbol} NeoData：name={nd_result.get('name')} industry={nd_result.get('industry')} MV={nd_result.get('total_mv',0):.0f} PE={nd_result.get('pe_ttm',0):.1f} | {elapsed:.1f}s")
            return nd_result
    except subprocess.TimeoutExpired:
        elapsed = time.time() - t0
        logger.warning(f"{symbol} NeoData：超时(25s) | {elapsed:.1f}s")
    except Exception as e:
        elapsed = time.time() - t0
        logger.warning(f"{symbol} NeoData：失败 [{type(e).__name__}: {e}] | {elapsed:.1f}s")
    return None


def _westock_profile(symbol: str) -> Optional[Dict]:
    """通过 westock-data profile 获取股票名称和行业（带缓存）"""
    if symbol in _westock_cache:
        return _westock_cache[symbol]

    t0 = time.time()
    try:
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
        elapsed = time.time() - t0
        output = r.stdout + r.stderr
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
            if wresult:
                logger.info(f"{symbol} westock-data：name={wresult.get('name')} industry={wresult.get('industry')} | {elapsed:.1f}s")
            return _westock_cache[symbol]
        else:
            logger.warning(f"{symbol} westock-data：表格行不足({len(lines)}行) | {elapsed:.1f}s")
    except subprocess.TimeoutExpired:
        elapsed = time.time() - t0
        logger.warning(f"{symbol} westock-data：超时(20s) | {elapsed:.1f}s")
    except Exception as e:
        elapsed = time.time() - t0
        logger.warning(f"{symbol} westock-data：失败 [{type(e).__name__}: {e}] | {elapsed:.1f}s")
    _westock_cache[symbol] = None
    return None


# 字段映射表
PROFIT_COLS = {
    'operating_income': 'revenue',
    'operating_costs': 'oper_cost',
    'operating_profit': 'oper_profit',
    'parent_holder_net_profit': 'net_profit_parent',
    'index_deduct_holder_net_profit': 'net_profit_ex',
    'interest_expenses': 'fin_expense',
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

PROFIT_METRICS = {'operating_income', 'operating_costs', 'operating_profit', 
                  'parent_holder_net_profit', 'index_deduct_holder_net_profit',
                  'interest_expenses', 'benefit_finance_fee'}
BALANCE_METRICS = {'assets_total', 'total_debt', 'parent_holder_equity_total',
                   'holder_equity_total', 'total_current_assets', 'current_total_debt'}
CASHFLOW_METRICS = {'act_cash_flow_net', 'pay_fixed_assets_etc_cash', 'sale_received_cash'}

FINAL_COLS = [
    'report_date', 'ann_date',
    'revenue', 'oper_cost', 'oper_profit',
    'net_profit_parent', 'net_profit_ex', 'fin_expense',
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
        t0 = time.time()
        try:
            df = api_func(symbol=symbol, indicator="按报告期")
            if df is None or df.empty:
                elapsed = time.time() - t0
                logger.warning(f"{symbol} {api_name}：返回空 | {elapsed:.1f}s")
                return None
            df = df[df['metric_name'].isin(needed_metrics)]
            if df.empty:
                elapsed = time.time() - t0
                logger.warning(f"{symbol} {api_name}：过滤后无匹配指标 | {elapsed:.1f}s")
                return None
            pivot = df.pivot_table(
                index='report_date', columns='metric_name',
                values='value', aggfunc='first'
            ).reset_index()
            elapsed = time.time() - t0
            logger.info(f"{symbol} {api_name}：{len(pivot)}行 | {elapsed:.1f}s")
            return pivot
        except Exception as e:
            elapsed = time.time() - t0
            logger.error(f"{symbol} {api_name}：失败 [{type(e).__name__}: {e}] | {elapsed:.1f}s")
            return None

    @classmethod
    def get_combined_financials(cls, symbol: str) -> pd.DataFrame:
        """获取个股完整财务数据，按报告期合并"""
        t_total = time.time()

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
            elapsed = time.time() - t_total
            logger.error(f"{symbol} 财务数据获取失败：利润表为空 | 总耗时{elapsed:.1f}s")
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
            elapsed = time.time() - t_total
            logger.error(f"{symbol} 财务数据获取失败：资产负债表为空 | 总耗时{elapsed:.1f}s")
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
            elapsed = time.time() - t_total
            logger.error(f"{symbol} 财务数据获取失败：现金流量表为空 | 总耗时{elapsed:.1f}s")
            return pd.DataFrame()

        # 4) 字段映射与合并
        # 4a) 财务费用优先级合并：interest_expenses > benefit_finance_fee
        # 两列都可能映射到 fin_expense，需在rename前合并
        # 注意：财务费用可能为0（利息收入>支出时），0是有效值不应视为空
        if 'interest_expenses' in profit.columns and 'benefit_finance_fee' in profit.columns:
            # 将空字符串转为NA，保留0值
            ie = profit['interest_expenses'].replace('', pd.NA).replace('0', 0).replace('0.0', 0)
            bf = profit['benefit_finance_fee'].replace('', pd.NA).replace('0', 0).replace('0.0', 0)
            # interest_expenses优先，仅NA值用benefit_finance_fee补
            profit['interest_expenses'] = ie.fillna(bf)
            profit = profit.drop(columns=['benefit_finance_fee'])
        elif 'benefit_finance_fee' in profit.columns and 'interest_expenses' not in profit.columns:
            # 只有benefit_finance_fee，映射为interest_expenses以便后续统一处理
            profit = profit.rename(columns={'benefit_finance_fee': 'interest_expenses'})
        
        profit = profit.rename(columns=PROFIT_COLS)
        balance = balance.rename(columns=BALANCE_COLS)
        cashflow = cashflow.rename(columns=CASHFLOW_COLS)

        profit = profit.loc[:, ~profit.columns.duplicated(keep='first')]
        balance = balance.loc[:, ~balance.columns.duplicated(keep='first')]
        cashflow = cashflow.loc[:, ~cashflow.columns.duplicated(keep='first')]

        profit['report_date'] = pd.to_datetime(profit['report_date'])
        balance['report_date'] = pd.to_datetime(balance['report_date'])
        cashflow['report_date'] = pd.to_datetime(cashflow['report_date'])

        df = pd.merge(profit, balance, on='report_date', how='inner')
        df = pd.merge(df, cashflow, on='report_date', how='inner')
        df['report_date'] = pd.to_datetime(df['report_date'])

        for col in FINAL_COLS:
            if col not in df.columns:
                df[col] = 0
        df = df[FINAL_COLS].sort_values('report_date')

        for col in FINAL_COLS:
            if col not in ('report_date', 'ann_date'):
                try:
                    df[col] = df[col].astype(float)
                except Exception:
                    df[col] = 0

        if 'fin_expense' in df.columns:
            df['fin_expense'] = df['fin_expense'].abs()

        def estimate_ann_date(report_date):
            month = report_date.month
            if month == 12: return report_date + pd.Timedelta(days=120)
            elif month == 3: return report_date + pd.Timedelta(days=30)
            elif month == 6: return report_date + pd.Timedelta(days=60)
            elif month == 9: return report_date + pd.Timedelta(days=30)
            else: return report_date + pd.Timedelta(days=45)
        
        df['ann_date'] = df['report_date'].apply(estimate_ann_date)

        elapsed = time.time() - t_total
        logger.info(f"{symbol} 财务数据合并完成：{len(df)}行 | 总耗时{elapsed:.1f}s")
        return df

    @staticmethod
    def get_stock_quote(symbol: str) -> Dict[str, float]:
        """
        获取实时行情（总市值、PE-TTM）
        降级链：全市场行情缓存 → 东方财富个股 → NeoData兜底
        """
        t0 = time.time()
        info = _fetch_stock_info(symbol)
        total_mv = info.get('total_mv', 0)
        pe = info.get('pe_ttm', 0)

        # 兜底：总市值/净利润估算PE
        if pe <= 0 and total_mv > 0:
            try:
                fin = ak.stock_financial_benefit_new_ths(symbol=symbol, indicator="按报告期")
                if fin is not None and not fin.empty:
                    latest_date = fin['report_date'].max()
                    net_profit_row = fin[(fin['metric_name'] == 'parent_holder_net_profit') &
                                         (fin['report_date'] == latest_date)]
                    if not net_profit_row.empty:
                        net_profit = float(net_profit_row['value'].values[0])
                        if net_profit > 0: pe = total_mv / net_profit
            except Exception as e:
                logger.warning(f"{symbol} PE兜底估算：失败 [{type(e).__name__}: {e}]")

        info['total_mv'] = total_mv
        info['pe_ttm'] = pe
        elapsed = time.time() - t0
        logger.info(f"{symbol} 行情获取完成：MV={total_mv:.0f} PE={pe:.1f} | {elapsed:.1f}s")
        return {'total_mv': total_mv, 'pe_ttm': pe}

    @staticmethod
    def get_stock_name(symbol: str) -> str:
        """获取股票名称"""
        info = _fetch_stock_info(symbol)
        name = info.get('name', symbol)
        if name and name != symbol:
            return name
        try:
            wp = _westock_profile(symbol)
            if wp and wp.get('name'):
                info['name'] = wp['name']
                return wp['name']
        except Exception as e:
            logger.warning(f"{symbol} 获取名称备用：失败 [{type(e).__name__}: {e}]")
        return symbol

    @staticmethod
    def get_industry(symbol: str) -> Optional[str]:
        """获取行业分类"""
        info = _fetch_stock_info(symbol)
        industry = info.get('industry')
        if industry:
            return industry
        try:
            wp = _westock_profile(symbol)
            if wp and wp.get('industry'):
                info['industry'] = wp['industry']
                return wp['industry']
        except Exception as e:
            logger.warning(f"{symbol} 获取行业备用：失败 [{type(e).__name__}: {e}]")
        return None

    @staticmethod
    def is_st_stock(symbol: str) -> bool:
        """判断是否 ST 股票"""
        name = DataProvider.get_stock_name(symbol)
        return 'ST' in name or '*ST' in name
