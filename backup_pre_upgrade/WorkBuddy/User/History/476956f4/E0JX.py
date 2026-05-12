#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Debug: test raw NeoData API response"""
import os, sys, json, logging
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from stock_analyzer import load_token, Config

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

token = load_token()
logger.info(f"Token loaded: {token[:20]}...")

import requests as req_lib

headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
payload = {"query": "300012.SZ 华测检测 年报"}

logger.info(f"POST {Config.NEODATA_URL}")
logger.info(f"Payload: {json.dumps(payload, ensure_ascii=False)}")

try:
    resp = req_lib.post(Config.NEODATA_URL, json=payload, headers=headers, timeout=50)
    logger.info(f"HTTP Status: {resp.status_code}")
    logger.info(f"Response headers: {dict(resp.headers)}")
    body = resp.text
    logger.info(f"Response body (first 2000 chars):\n{body[:2000]}")
    
    try:
        data = resp.json()
        logger.info(f"JSON parsed successfully")
        logger.info(f"Top-level keys: {list(data.keys()) if isinstance(data, dict) else type(data)}")
        if isinstance(data.get("data"), dict):
            inner = data["data"]
            logger.info(f"data dict keys: {list(inner.keys())}")
            text_val = inner.get("text", "")
            logger.info(f"data.text length: {len(text_val)}")
            logger.info(f"data.text preview: {text_val[:500]}")
    except Exception as e:
        logger.error(f"JSON parse error: {e}")
except Exception as e:
    logger.error(f"Request failed: {e}")
