#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================================
 A股智能选股系统 V6.0.0
 参考格式输出：股票代码 | 股票名称 | 行业 | 财务指标 | 评分 | 评级
 数据流程：AKShare → SQLite → 计算 → 评分 → Excel
================================================================================
"""
import argparse
from datetime import datetime
from typing import List, Optional, Dict, Tuple
import os
import sys
import json
import sqlite3
import logging
import threading
import time
import pandas as pd

from config import VETO_RULES
from scorer import Scorer
from data_provider import DataProvider
from calculator import IndicatorCalculator
from excel_export import save_to_excel


# 全局变量
_eval_date = None
_calendar = None


# ============================================================================
# 模拟数据
# ============================================================================
MOCK_DATA = {
    '600519': {
        'name': '贵州茅台', 'industry': '食品饮料',
        'roe_ttm': 30.5, 'gross_margin_ttm': 91.5, 'net_margin_ttm': 52.3,
        'q_revenue_yoy': 18.5, 'q_net_profit_yoy': 20.2,
        'asset_liability_ratio': 15.2, 'de_ratio': 0.18, 'current_ratio': 4.5,
        'net_profit_ratio': 136.5, 'net_profit_ttm': 880.5, 'ocf_ttm': 1200.5,
        'pe_ttm': 28.5, 'total_mv': 25000.0,
        'annual_report_date': '2024-04-27', 'latest_quarter': '2024-12-31', 'data_completeness': 100,
        'quarter_coverage': '4/4', 'field_gaps': '无',
        'veto': '否', 'veto_reason': '',
    },
    '000858': {
        'name': '五粮液', 'industry': '食品饮料',
        'roe_ttm': 18.2, 'gross_margin_ttm': 75.8, 'net_margin_ttm': 35.2,
        'q_revenue_yoy': 25.3, 'q_net_profit_yoy': 45.7,
        'asset_liability_ratio': 32.5, 'de_ratio': 0.48, 'current_ratio': 2.8,
        'net_profit_ratio': 115.2, 'net_profit_ttm': 215.5, 'ocf_ttm': 295.5,
        'pe_ttm': 22.5, 'total_mv': 8500.0,
        'annual_report_date': '2024-04-27', 'latest_quarter': '2024-12-31', 'data_completeness': 100,
        'quarter_coverage': '4/4', 'field_gaps': '无',
        'veto': '否', 'veto_reason': '',
    },
    '002415': {
        'name': '海康威视', 'industry': '电子',
        'roe_ttm': 22.5, 'gross_margin_ttm': 45.2, 'net_margin_ttm': 18.5,
        'q_revenue_yoy': 12.8, 'q_net_profit_yoy': 15.3,
        'asset_liability_ratio': 38.5, 'de_ratio': 0.62, 'current_ratio': 2.2,
        'net_profit_ratio': 95.5, 'net_profit_ttm': 145.2, 'ocf_ttm': 138.5,
        'pe_ttm': 25.8, 'total_mv': 3200.0,
        'annual_report_date': '2024-04-27', 'latest_quarter': '2024-12-31', 'data_completeness': 100,
        'quarter_coverage': '4/4', 'field_gaps': '无',
        'veto': '否', 'veto_reason': '',
    },
    '999999': {
        'name': '高杠杆股', 'industry': '钢铁',
        'roe_ttm': 5.2, 'gross_margin_ttm': 15.5, 'net_margin_ttm': 3.2,
        'q_revenue_yoy': -10.5, 'q_net_profit_yoy': -25.0,
        'asset_liability_ratio': 92.5, 'de_ratio': 12.5, 'current_ratio': 0.45,
        'net_profit_ratio': -45.0, 'net_profit_ttm': -20.5, 'ocf_ttm': -50.0,
        'pe_ttm': 0, 'total_mv': 500.0,
        'annual_report_date': '2024-04-27', 'latest_quarter': '2024-12-31', 'data_completeness': 100,
        'quarter_coverage': '4/4', 'field_gaps': '无',
        'veto': '是', 'veto_reason': '经营现金流为负',
    },
}


# ============================================================================
# 评级与置信度
# ============================================================================

def get_rating(score: float) -> str:
    """根据总分返回评级"""
    if score >= 80:
        return 'A+'
    elif score >= 70:
        return 'A'
    elif score >= 60:
        return 'B+'
    elif score >= 50:
        return 'B'
    elif score >= 40:
        return 'C'
    else:
        return 'D'


def get_confidence(score: float, completeness: float) -> str:
    """置信度评估"""
    if completeness < 80:
        return '低（数据不足）'
    elif score >= 70:
        return '高'
    elif score >= 50:
        return '中'
    else:
        return '中（需验证）'
