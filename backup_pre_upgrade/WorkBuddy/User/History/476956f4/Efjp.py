#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Debug: test run_neodata with fixed parsing"""
import os, sys, logging
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from stock_analyzer import load_token, run_neodata, _extract_annual_block, parse_financial_all

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

token = load_token()
logger.info(f"Token loaded: {token[:20]}...")

# Test with one stock
query = "300012.SZ 华测检测 年报"
logger.info(f"Query: {query}")

text = run_neodata(query, token)
logger.info(f"Returned text length: {len(text)}")
logger.info(f"Text preview (first 300 chars):\n{text[:300]}")

block = _extract_annual_block(text)
logger.info(f"Annual block length: {len(block)}")
if block:
    logger.info(f"Annual block preview:\n{block[:500]}")
    metrics = parse_financial_all(block)
    logger.info(f"Parsed metrics: {metrics}")
else:
    logger.warning("No annual block found!")
