#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""annual_scorer 核心逻辑单元测试"""

import sys, os, re, tempfile
sys.path.insert(0, os.path.dirname(__file__))

# ---- 静默日志，不写文件 ----
import logging
logging.basicConfig(level=logging.CRITICAL)

# ---- 导入目标模块（绕过 setup_logging 写文件的副作用） ----
import importlib, types

# 先 patch setup_logging 再导入
import unittest.mock as mock
with mock.patch('logging.FileHandler', mock.MagicMock()):
    import annual_scorer as m

# 重新把 logger 替换成静默 logger，避免输出干扰
m.logger = logging.getLogger("silent")

PASS = "\033[32m[OK]\033[0m"
FAIL = "\033[31m[FAIL]\033[0m"
errors = []

def check(name, cond, detail=""):
    if cond:
        print(f"{PASS} {name}")
    else:
        print(f"{FAIL} {name}  {detail}")
        errors.append(name)

# ==============================
# 1. parse_num
# ==============================
check("parse_num / 百分比", m.parse_num("15.3%") == 15.3)
check("parse_num / 负百分比", m.parse_num("-5.7%") == -5.7)
check("parse_num / 普通数字", m.parse_num("123.45") == 123.45)
check("parse_num / None 输入", m.parse_num(None) is None)
check("parse_num / 空字符串", m.parse_num("") is None)

# ==============================
# 2. _parse_num_from_line
# ==============================
check("_parse_num_from_line / 亿元", m._parse_num_from_line("净利润 3.5亿元") == 3.5e8)
check("_parse_num_from_line / 万亿元", m._parse_num_from_line("营收 1.2万亿元") == 1.2e12)
check("_parse_num_from_line / 万元", m._parse_num_from_line("费用 500万元") == 5e6)
check("_parse_num_from_line / 无单位", m._parse_num_from_line("数值 100") is None)
check("_parse_num_from_line / None", m._parse_num_from_line(None) is None)

# ==============================
# 3. percentile_rank
# ==============================
vals = [10.0, 20.0, 30.0, 40.0, 50.0]
check("percentile_rank / 中间值=60", m.percentile_rank(30.0, vals) == 60.0)
check("percentile_rank / 最大值=100", m.percentile_rank(50.0, vals) == 100.0, f"got {m.percentile_rank(50.0, vals)}")
check("percentile_rank / 最小值=20", m.percentile_rank(10.0, vals) == 20.0, f"got {m.percentile_rank(10.0, vals)}")
check("percentile_rank / None输入=0", m.percentile_rank(None, vals) == 0.0)
check("percentile_rank / 空列表=50", m.percentile_rank(50.0, []) == 50.0)
# reverse
check("percentile_rank / reverse最小值=80", m.percentile_rank(10.0, vals, reverse=True) == 80.0,
      f"got {m.percentile_rank(10.0, vals, reverse=True)}")
check("percentile_rank / reverse最大值=0", m.percentile_rank(50.0, vals, reverse=True) == 0.0,
      f"got {m.percentile_rank(50.0, vals, reverse=True)}")

# ==============================
# 4. calc_completeness
# ==============================
full = {'roe':15,'gross_margin':30,'net_margin':10,'revenue_yoy':5,
        'profit_yoy':8,'debt_ratio':45,'net_profit':1e8,'ocf_abs':1.2e8}
empty = {k:None for k in full}
partial = {**full, 'gross_margin':None, 'net_margin':None}

ratio, level = m.calc_completeness(full)
check("calc_completeness / 全量=high", level == "high", f"got {level}")

ratio2, level2 = m.calc_completeness(empty)
check("calc_completeness / 全空=ultra_low", level2 == "ultra_low", f"got {level2}")

ratio3, level3 = m.calc_completeness(partial)
check("calc_completeness / 6/8=medium or high", level3 in ("medium","high"), f"got {level3}")

# ==============================
# 5. load_stock_list
# ==============================
with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', encoding='utf-8', delete=False) as f:
    f.write("600519 贵州茅台\n000001 平安银行\n688001 中芯国际\n300750 宁德时代\n430001 测试北交所\n")
    fname = f.name
stocks = m.load_stock_list(fname)
os.unlink(fname)
codes = [s['ts_code'] for s in stocks]
check("load_stock_list / 上交所后缀", "600519.SH" in codes)
check("load_stock_list / 深交所后缀", "000001.SZ" in codes)
check("load_stock_list / 创业板保留", "300750.SZ" in codes)
check("load_stock_list / 科创板过滤", not any("688001" in c for c in codes))
check("load_stock_list / 北交所过滤", not any("430001" in c for c in codes))

# ==============================
# 6. _extract_annual_block
# ==============================
sample = (
    "前面文字统计截止日期为20231231的年报\n"
    "ROE 15%\n净利润 3亿元\n"
    "统计截止日期为20221231的年报\n"
    "ROE 12%\n"
)
block23 = m._extract_annual_block(sample, 2023)
check("_extract_annual_block / 精确年份", "ROE 15%" in block23 and "ROE 12%" not in block23,
      f"block={block23[:80]}")

block_latest = m._extract_annual_block(sample)
check("_extract_annual_block / 最新年份", "ROE 12%" in block_latest,
      f"block={block_latest[:80]}")

# ==============================
# 7. parse_financial_all
# ==============================
fin_block = (
    "加权净资产收益率ROE 18.5%\n"
    "销售毛利率 35.2%\n"
    "销售净利率 12.8%\n"
    "营业收入同比增长 8.3%\n"
    "归母净利润同比增长 -2.1%\n"
    "资产负债率 42.6%\n"
    "净利润 25.6亿元\n"
    "经营活动产生的现金流量净额 30.1亿元\n"
)
fin = m.parse_financial_all(fin_block)
check("parse_financial_all / ROE", fin["roe"] == 18.5, f"got {fin['roe']}")
check("parse_financial_all / gross_margin", fin["gross_margin"] == 35.2, f"got {fin['gross_margin']}")
check("parse_financial_all / net_margin", fin["net_margin"] == 12.8, f"got {fin['net_margin']}")
check("parse_financial_all / revenue_yoy", fin["revenue_yoy"] == 8.3, f"got {fin['revenue_yoy']}")
check("parse_financial_all / profit_yoy", fin["profit_yoy"] == -2.1, f"got {fin['profit_yoy']}")
check("parse_financial_all / debt_ratio", fin["debt_ratio"] == 42.6, f"got {fin['debt_ratio']}")
check("parse_financial_all / net_profit", abs(fin["net_profit"] - 25.6e8) < 1, f"got {fin['net_profit']}")
check("parse_financial_all / ocf_abs", abs(fin["ocf_abs"] - 30.1e8) < 1, f"got {fin['ocf_abs']}")

# ==============================
# 8. calc_score（端到端）
# ==============================
base = {'roe':15,'gross_margin':30,'net_margin':10,'revenue_yoy':5,'profit_yoy':8,
        'debt_ratio':45,'net_profit':1e9,'ocf_abs':1.2e9,'fetch_success':True,'report_date':'20231231'}
target = {'ts_code':'000001.SZ','name':'平安银行','industry_l1':'银行', **base}
peers = [{'ts_code':f'00000{i}.SZ','name':f'测试{i}','industry_l1':'银行',
          'roe':i*2,'gross_margin':i*3,'net_margin':i,'revenue_yoy':i,'profit_yoy':i,
          'debt_ratio':30+i,'net_profit':1e8*i,'ocf_abs':1.1e8*i,
          'fetch_success':True,'report_date':'20231231'} for i in range(1,9)]
all_s = [target] + peers
ind_g = {'银行': all_s}

score = m.calc_score(target, ind_g, all_s)
check("calc_score / total_score范围", 0 <= score['total_score'] <= 100,
      f"got {score['total_score']}")
check("calc_score / grade合法", score['grade'] in ('A','B','C','D','E'))
check("calc_score / confidence合法", score['confidence'] in ('高','中','低'))

# 亏损惩罚测试
loss_stock = {**target, 'ts_code':'000002.SZ', 'net_profit':-1e8, 'ocf_abs':-5e7}
loss_score = m.calc_score(loss_stock, ind_g, all_s)
check("calc_score / 亏损上限", loss_score['total_score'] <= m.Config.NEGATIVE_PROFIT_PENALTY + 0.001,
      f"got {loss_score['total_score']}")

# ==============================
# 汇总
# ==============================
print()
total_checks = 36
if errors:
    print(f"\033[31m测试失败 {len(errors)}/{total_checks}: {errors}\033[0m")
    sys.exit(1)
else:
    print(f"\033[32m全部 {total_checks} 项测试通过 OK\033[0m")
    sys.exit(0)
