#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================================
 五维加权评分器 V6.0.0
 成长性(25%) + 盈利能力(30%) + 现金流质量(20%) + 偿债风险(15%) + 估值(10%)
 新增：一票否决机制 + 行业百分位中性化
================================================================================
"""
from typing import Dict, Optional
from config import WEIGHTS, THRESHOLDS, VETO_RULES, INDUSTRY_CONFIG
from calculator import IndicatorCalculator


class Scorer:
    """
    基于财务指标计算五维评分和综合评分。
    支持一票否决机制和行业百分位中性化。
    """

    def __init__(self, ind: IndicatorCalculator, quote: Dict[str, float],
                 industry: Optional[str] = None, industry_stats: Optional[Dict] = None):
        self.ind = ind
        self.quote = quote
        self.industry = industry
        self.industry_stats = industry_stats  # 行业统计数据（用于百分位计算）
        self._veto_applied = False
        self._veto_reason = None

    # -------------------------------------------------------------------------
    # 评分辅助函数
    # -------------------------------------------------------------------------
    @staticmethod
    def _linear_score(value: float, threshold: float) -> float:
        """线性得分（正向：值越大越好）"""
        if threshold <= 0:
            return 0.0
        return max(0.0, min(100.0, (value / threshold) * 100))

    @staticmethod
    def _reverse_score(value: float, threshold: float) -> float:
        """反向得分（反向：值越低越好）"""
        if threshold <= 0:
            return 0.0
        return max(0.0, min(100.0, (1 - value / threshold) * 100))

    @staticmethod
    def _zero_score(value: float, threshold: float) -> float:
        """零值保护得分（值为负/零时得 0 分）"""
        if value <= 0:
            return 0.0
        return Scorer._linear_score(value, threshold)

    @staticmethod
    def _percentile_score(value: float, p25: float, p75: float, target: float = 50) -> float:
        """
        百分位得分：根据行业中位数调整。
        p25/p75 为行业中 25% 和 75% 分位值。
        得分 = 在行业中的相对位置（0-100）
        """
        if p75 <= p25:
            return 50.0  # 无法判断，返回中性分

        # 标准化到 0-100
        normalized = (value - p25) / (p75 - p25) * 100
        return max(0.0, min(100.0, normalized))

    # -------------------------------------------------------------------------
    # 一票否决检查
    # -------------------------------------------------------------------------
    def _check_veto(self) -> bool:
        """
        检查是否触发一票否决。
        返回 True 表示触发否决，False 表示正常。
        """
        if not VETO_RULES['enable']:
            return False

        # 1. 现金流得分否决
        cashflow_score = self.cashflow_score()
        if cashflow_score < VETO_RULES['min_cashflow_score']:
            self._veto_applied = True
            self._veto_reason = f"现金流得分{cashflow_score:.1f}低于阈值{VETO_RULES['min_cashflow_score']}"
            return True

        # 2. D/E 过高否决
        if self.ind.de_ratio > VETO_RULES['max_de_ratio']:
            self._veto_applied = True
            self._veto_reason = f"D/E={self.ind.de_ratio:.2f}超过阈值{VETO_RULES['max_de_ratio']}"
            return True

        # 3. 资产负债率过高否决
        if self.ind.asset_liability_ratio / 100 > VETO_RULES['max_asset_liability']:
            self._veto_applied = True
            self._veto_reason = f"资产负债率={self.ind.asset_liability_ratio:.1f}%超过阈值{VETO_RULES['max_asset_liability']*100:.0f}%"
            return True

        # 4. 经营现金流为负否决
        if self.ind.ocf_ttm < VETO_RULES['min_ocf_ttm']:
            self._veto_applied = True
            self._veto_reason = f"TTM经营现金流{self.ind.ocf_ttm:.0f}亿元为负"
            return True

        return False

    # -------------------------------------------------------------------------
    # 五维评分
    # -------------------------------------------------------------------------
    def growth_score(self) -> float:
        """
        成长性评分 (25%)
        - 单季归母净利润同比 (60%)
        - 单季营收同比 (40%)
        """
        s1 = self._zero_score(
            self.ind.q_net_profit_yoy,
            THRESHOLDS['q_net_profit_yoy_threshold'] * 100
        )
        s2 = self._zero_score(
            self.ind.q_revenue_yoy,
            THRESHOLDS['q_revenue_yoy_threshold'] * 100
        )
        return round(s1 * 0.6 + s2 * 0.4, 2)

    def profitability_score(self) -> float:
        """
        盈利能力评分 (30%)
        - TTM ROE (70%)
        - TTM 毛利率 (30%)
        """
        s1 = self._linear_score(
            self.ind.roe_ttm,
            THRESHOLDS['roe_ttm_threshold'] * 100
        )
        s2 = self._linear_score(
            self.ind.gross_margin_ttm,
            THRESHOLDS['gross_margin_ttm_threshold'] * 100
        )
        return round(s1 * 0.7 + s2 * 0.3, 2)

    def cashflow_score(self) -> float:
        """
        现金流质量评分 (20%)
        - 净现比 (40%)
        - 自由现金流收益率 (30%)
        - 销售收现比 (30%)
        """
        s1 = self._linear_score(
            self.ind.net_profit_ratio,
            THRESHOLDS['net_profit_ratio_threshold']
        )
        fcf_yield = (self.ind.fcf_ttm / self.quote['total_mv']) if self.quote.get('total_mv', 0) > 0 else 0
        s2 = self._linear_score(
            fcf_yield,
            THRESHOLDS['fcf_yield_threshold']
        )
        s3 = self._linear_score(
            self.ind.cash_recovery_rate,
            THRESHOLDS['cash_recovery_threshold']
        )
        return round(s1 * 0.4 + s2 * 0.3 + s3 * 0.3, 2)

    def leverage_score(self) -> float:
        """
        偿债风险评分 (15%)
        - D/E 越低越好 (40%)
        - 流动比率 越高越好 (30%)
        - 资产负债率 越低越好 (30%)
        """
        s1 = self._reverse_score(
            self.ind.de_ratio,
            THRESHOLDS['de_ratio_threshold']
        )
        s2 = self._linear_score(
            self.ind.current_ratio,
            THRESHOLDS['current_ratio_threshold']
        )
        s3 = self._reverse_score(
            self.ind.asset_liability_ratio / 100,
            THRESHOLDS['asset_liability_threshold']
        )
        return round(s1 * 0.4 + s2 * 0.3 + s3 * 0.3, 2)

    def valuation_score(self) -> float:
        """
        估值评分 (10%)
        - PE-TTM 越低越好
        - PE ≤ 0 得 0 分
        """
        pe = self.quote.get('pe_ttm', 0)
        if pe <= 0:
            return 0.0
        return round(self._reverse_score(
            pe,
            THRESHOLDS['pe_ttm_threshold']
        ), 2)

    # -------------------------------------------------------------------------
    # 综合评分
    # -------------------------------------------------------------------------
    def total_score(self) -> Dict[str, float]:
        """计算五维评分和综合评分（含否决机制）"""
        scores = {
            'growth': self.growth_score(),
            'profitability': self.profitability_score(),
            'cash_flow': self.cashflow_score(),
            'leverage': self.leverage_score(),
            'valuation': self.valuation_score(),
        }

        # 【一票否决检查】
        if self._check_veto():
            scores['total_score'] = 0.0
            scores['veto'] = True
            scores['veto_reason'] = self._veto_reason
        else:
            # 加权综合分
            total = sum(scores[k] * WEIGHTS[k] for k in ['growth', 'profitability', 'cash_flow', 'leverage', 'valuation'])
            scores['total_score'] = round(total, 2)
            scores['veto'] = False

        return scores

    # -------------------------------------------------------------------------
    # 行业百分位得分（待批量计算后调用）
    # -------------------------------------------------------------------------
    def industry_adjusted_score(self, raw_scores: Dict[str, float]) -> Dict[str, float]:
        """
        行业百分位中性化调整。
        将原始得分替换为行业百分位得分，避免系统天然偏向高 ROE 行业。
        """
        if not INDUSTRY_CONFIG['enable'] or not self.industry_stats:
            return raw_scores

        adjusted = raw_scores.copy()

        # 盈利能力行业调整
        if 'profitability' in self.industry_stats:
            stats = self.industry_stats['profitability']
            adjusted['profitability'] = self._percentile_score(
                raw_scores['profitability'],
                stats.get('p25', 30), stats.get('p75', 80)
            )

        # 类似地调整其他维度...

        # 重新计算总分
        total = sum(adjusted[k] * WEIGHTS[k] for k in ['growth', 'profitability', 'cash_flow', 'leverage', 'valuation'])
        adjusted['total_score'] = round(total, 2)
        adjusted['industry_adjusted'] = True

        return adjusted