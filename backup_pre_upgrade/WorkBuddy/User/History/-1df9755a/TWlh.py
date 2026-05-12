
def _mock_evaluate(symbol: str) -> Optional[Dict]:
    """模拟评估（通用，随机生成真实感数据）"""
    import random
    from scorer import Scorer

    industry_defaults = {
        '食品饮料': {'roe': (20, 35), 'gm': (40, 95), 'nm': (10, 55)},
        '电子': {'roe': (10, 25), 'gm': (25, 50), 'nm': (5, 20)},
        '医药': {'roe': (12, 25), 'gm': (50, 80), 'nm': (10, 30)},
        '电力': {'roe': (8, 18), 'gm': (20, 40), 'nm': (5, 15)},
        '钢铁': {'roe': (2, 15), 'gm': (5, 20), 'nm': (-5, 10)},
        '房地产': {'roe': (5, 20), 'gm': (15, 35), 'nm': (3, 15)},
    }

    prefix = symbol[:3]
    if prefix in ['600', '601', '603', '605']:
        industry = random.choice(list(industry_defaults.keys()))
    elif prefix in ['000', '001']:
        industry = random.choice(['电子', '医药', '电力', '房地产'])
    elif prefix in ['002']:
        industry = random.choice(['电子', '医药', '化工', '机械'])
    elif prefix in ['300']:
        industry = random.choice(['电子', '医药', '软件', '化工'])
    elif prefix in ['301']:
        industry = random.choice(['软件', '医药', '电子', '化工'])
    else:
        industry = random.choice(list(industry_defaults.keys()))

    name = f"{industry[:2]}{symbol[-2:]}"
    ranges = industry_defaults.get(industry, industry_defaults['电子'])

    roe = round(random.uniform(*ranges['roe']), 2)
    gm = round(random.uniform(*ranges['gm']), 2)
    rev_yoy = round(random.uniform(-10, 50), 2)
    profit_yoy = round(random.uniform(-20, 80), 2)
    alr = round(random.uniform(20, 80), 2)
    de = round(random.uniform(0.1, 2.0), 2)
    cr = round(random.uniform(0.8, 4.0), 2)
    ocf_ratio = round(random.uniform(50, 150), 2)
    profit = round(random.uniform(1, 500), 2)
    ocf = round(profit * random.uniform(0.5, 1.5), 2)
    pe = round(random.uniform(10, 60), 2)
    mv = round(random.uniform(50, 5000), 2)

    if symbol == '999999':
        roe, gm = 5.2, 15.5
        rev_yoy, profit_yoy = -10.5, -25.0
        alr, de, cr = 92.5, 12.5, 0.45
        ocf_ratio, profit, ocf = -45.0, -20.5, -50.0
        industry = '钢铁'

    veto = '否'
    veto_reason = ''
    if ocf < 0:
        veto = '是'
        veto_reason = '经营现金流为负'
    elif de > 3.0:
        veto = '是'
        veto_reason = f'D/E={de:.1f}超过阈值'
    elif alr > 90:
        veto = '是'
        veto_reason = f'资产负债率={alr:.1f}%超过90%'

    class MockCalc:
        roe_ttm = roe
        gross_margin_ttm = gm
        de_ratio = de
        asset_liability_ratio = alr
        ocf_ttm = ocf * 100000000
        _ttm_capex = ocf * 20000000
        fcf_ttm = (ocf * 100000000) - (ocf * 20000000)
        net_profit_ratio = ocf_ratio
        cash_recovery_rate = 1.1
        q_net_profit_yoy = profit_yoy
        q_revenue_yoy = rev_yoy
        current_ratio = cr
        net_profit_ttm = profit * 100000000

    class MockQuote(dict):
        def __init__(self):
            super().__init__()
            self['total_mv'] = mv * 100000000
            self['pe_ttm'] = pe

    calc = MockCalc()
    quote = MockQuote()
    scorer = Scorer(calc, quote)
    scores = scorer.total_score()

    if veto == '是':
        scores['total_score'] = 0.0
        scores['veto'] = True
        scores['veto_reason'] = veto_reason

    return {
        'symbol': symbol, 'name': name, 'industry': industry,
        'q_revenue_yoy': rev_yoy, 'q_net_profit_yoy': profit_yoy,
        'roe_ttm': roe, 'gross_margin_ttm': gm,
        'net_profit_ttm': profit, 'ocf_ttm': ocf,
        'capex_ttm': ocf * 0.2, 'fcf_ttm': ocf * 0.8,
        'net_profit_ratio': ocf_ratio,
        'fcf_yield': round((ocf * 0.8) / mv if mv > 0 else 0, 4),
        'cash_recovery_rate': 1.1,
        'de_ratio': de, 'current_ratio': cr, 'asset_liability_ratio': alr,
        'pe_ttm': pe, 'total_mv': mv,
        'annual_report_date': '2024-04-27', 'latest_quarter': '2024-12-31',
        'data_completeness': 100, 'quarter_coverage': '4/4', 'field_gaps': '无',
        'total_score': scores['total_score'],
        'rating': get_rating(scores['total_score']),
        'confidence': get_confidence(scores['total_score'], 100),
        'profitability': round(scores['profitability'], 2),
        'growth': round(scores['growth'], 2),
        'cash_flow_quality': round(scores['cash_flow'], 2),
        'leverage_risk': round(scores['leverage'], 2),
        'veto': veto, 'veto_reason': veto_reason,
    }
