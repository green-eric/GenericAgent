"""Test BFM service response time and data loading"""
import time
import requests
import json

BASE_URL = "http://localhost:9004"

def test_core():
    start = time.time()
    try:
        r = requests.get(f"{BASE_URL}/data?type=core", timeout=30)
        elapsed = time.time() - start
        d = r.json()
        
        print(f"=== /data?type=core ===")
        print(f"Response time: {elapsed:.1f}s")
        print(f"Top-level keys: {list(d.keys())}")
        print(f"Status: {d.get('status')}")
        
        data = d.get("data", d)  # data might be top-level
        if isinstance(data, dict):
            news = data.get("news", {})
            print(f"Data keys: {list(data.keys())[:15]}")
            print(f"Quick start mode: {data.get('_quick_start_mode', 'N/A')}")
            print(f"Warming up: {data.get('_warming_up', 'N/A')}")
            print(f"Message: {data.get('_message', 'N/A')}")
            print(f"All news count: {len(news.get('all_news', []))}")
            print(f"Picks count: {len(data.get('picks', []))}")
            print(f"Hot8 count: {len(data.get('hot8', []))}")
            print(f"Sectors count: {len(data.get('sector_heat', {}))}")
        else:
            print(f"Data type: {type(data)}")
            # Print first 500 chars of response
            print(f"Raw (first 500): {json.dumps(d, ensure_ascii=False)[:500]}")
    except requests.exceptions.Timeout:
        elapsed = time.time() - start
        print(f"TIMEOUT after {elapsed:.1f}s")
    except Exception as e:
        elapsed = time.time() - start
        print(f"ERROR after {elapsed:.1f}s: {e}")

def test_homepage():
    start = time.time()
    try:
        r = requests.get(BASE_URL, timeout=5)
        elapsed = time.time() - start
        print(f"\n=== Homepage ===")
        print(f"Response time: {elapsed:.1f}s, Status: {r.status_code}")
    except Exception as e:
        print(f"\nHomepage error: {e}")

if __name__ == "__main__":
    test_homepage()
    test_core()
