#!/usr/bin/env python3
import asyncio, json, ssl
from pathlib import Path
import aiohttp

TOKEN_FILE = Path.home() / ".workbuddy" / ".neodata_token"
token = TOKEN_FILE.read_text().strip()
print(f"Token length: {len(token)}")

async def test():
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}",
    }
    payload = {
        "query": "000001.SZ 平安银行 年报",
        "channel": "neodata",
        "sub_channel": "workbuddy",
        "data_type": "api",
    }
    async with aiohttp.ClientSession() as session:
        async with session.post(
            "https://copilot.tencent.com/agenttool/v1/neodata",
            headers=headers,
            json=payload,
            timeout=aiohttp.ClientTimeout(total=30),
            ssl=False,
        ) as resp:
            print(f"Status: {resp.status}")
            body = await resp.text()
            print(f"Body: {body[:500]}")

asyncio.run(test())
