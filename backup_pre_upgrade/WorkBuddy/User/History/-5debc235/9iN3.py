#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""测试按年份查询"""
import requests, re

TOKEN = "eyJhbGciOiJSUzI1NiIsInR5cCIgOiAiSldUIiwia2lkIiA6ICJteWZFenA3ODNLaV9KQ3g4Vm5jM1hfaXg2alpyYjZDZjVPTWtHWk1QSTNzIn0.eyJleHAiOjE4MDc5NzYzNDEsImlhdCI6MTc3NjkzNDIxOCwiYXV0aF90aW1lIjoxNzc2NDQwMzQyLCJqdGkiOiJhZGYzYzFkNi1kN2FlLTQ4ZGItYjg1Mi1lMTI3YjY2MTVjOGMiLCJpc3MiOiJodHRwczovL3d3dy5jb2RlYnVkZHkuY24vYXV0aC9yZWFsbXMvY29waWxvdCIsImF1ZCI6ImFjY291bnQiLCJzdWIiOiJjYWY4Y2NkZC1hNjE4LTQ3MDEtOGVkZS02ZDhkMTNjZjI5MjAiLCJ0eXAiOiJCZWFyZXIiLCJhenAiOiJjb25zb2xlIiwic2lkIjoiNmNlZjhlOTktYTYzYi00NGM1LWE1NjAtNjY4YWMyNTFjN2E5IiwiYWNyIjoiMCIsImFsbG93ZWQtb3JpZ2lucyI6WyIqIl0sInJlYWxtX2FjY2VzcyI6eyJyb2xlcyI6WyJkZWZhdWx0LXJvbGVzIiwib2ZmbGluZV9hY2Nlc3MiLCJ1bWFfYXV0aG9yaXphdGlvbiJdfSwicmVzb3VyY2VfYWNjZXNzIjp7ImFjY291bnQiOnsicm9sZXMiOlsibWFuYWdlLWFjY291bnQiLCJtYW5hZ2UtYWNjb3VudC1saW5rcyIsInZpZXctcHJvZmlsZSJdfX0sInNjb3BlIjoib3BlbmlkIHByb2ZpbGUgb2ZmbGluZV9hY2Nlc3MgZW1haWwiLCJlbWFpbF92ZXJpZmllZCI6ZmFsc2UsIm5pY2tuYW1lIjoi6Z2Z5rC05rWB5rexIiwicHJlZmVycmVkX3VzZXJuYW1lIjoiMTMwNjI4ODQyNTMifQ.h0E0KtMPMZG07c0hpbkolsoEnarS0s2P5QgmClNcIIkDFYemp79_iX_uEV4fKArp1jZZDaMfN03y19EDxf-VfTl_DT-u7ZlbGDn1h_tbBvhNoVdR9Z34xC2HU5lAA7wUyFASDSsJNek2rGOkIEHYIQa9rm3WlLsAfZAg594QTwUp_TF-mzuJnfg44GIYHGfVsNszJKlI5caJfyJyd1R52LlvZfK7MJ7EdO_tZNehqO6jekIVIYVynBaO3wRZMikod3K7i-_V7YxKHY_EZW_QMJ0v1JCc4pyDSKLEIZjYPHH9tjTQNCGg3sPIv1joESCGeYGChBBRi4VW5SR8TXCkDQ"

url = "https://copilot.tencent.com/agenttool/v1/neodata"
headers = {"Content-Type": "application/json", "Authorization": f"Bearer {TOKEN}"}

# 试查2023年年报
payload = {
    "query": "圣邦股份300661.SZ 2023年年报归母净利润",
    "channel": "neodata",
    "sub_channel": "workbuddy",
    "data_type": "api"
}
r = requests.post(url, headers=headers, json=payload, timeout=30)
d = r.json()
items = d.get("data", {}).get("apiData", {}).get("apiRecall", [])
print(f"条数: {len(items)}")
for it in items:
    content = it.get("content", "")
    m = re.search(r"截止日期为(\d{8})", content)
    period = m.group(1) if m else "N/A"
    tp = it.get("type", "")
    print(f"type={tp} period={period}")
    print(content[:400])
    print("---")
