"""Test BFM service response time and data loading"""
import time
import requests

BASE_URL = "http://localhost:9004"

def test_core():
    start = time.time()
    try:
        r = requests.get(f"{BASE_URL}/data?type=core", timeout=30)
        elapsed = time.time() - start
        d = r.json()
        data = d.get("data", {})
        news = data.get("news", {})
        
        print(f"=== /data?type=core ===")
        print(f"Response time: {elapsed:.1f}s")
        print(f"Status: {d.get('status')}")
        print(f"Quick start mode: {data.get('_quick_start_mode', 'N/A')}")
        print(f"Warming up: {data.get('_warming_up', 'N/A')}")
        print(f"Message: {data.get('_message', 'N/A')}")
        print(f"All news count: {len(news.get('all_news', []))}")
        print(f"Top news count: {len(news.get('top_news', []))}")
        print(f"Recent news count: {len(news.get('recent_news', []))}")
        print(f"Picks count: {len(data.get('picks', []))}")
        print(f"Hot8 count: {len(data.get('hot8', []))}")
        print(f"Sectors count: {len(data.get('sector_heat', {}))}")
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
